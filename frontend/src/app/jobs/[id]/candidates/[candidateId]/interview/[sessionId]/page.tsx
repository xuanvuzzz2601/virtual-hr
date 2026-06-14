"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { candidatesApi, interviewsApi } from "@/lib/api";
import { Candidate, GeminiSessionConfig, InterviewEvaluation, InterviewSession, TranscriptMessage } from "@/types";
import { cn, getScoreColor } from "@/lib/utils";

type Phase = "ready" | "connecting" | "interviewing" | "completing" | "completed" | "error";

// Model per Live API skill docs — gemini-live-2.5-flash-preview deprecated Dec 2025
const LIVE_MODEL = "gemini-3.1-flash-live-preview";

export default function InterviewPage() {
  const { id, candidateId, sessionId } = useParams<{ id: string; candidateId: string; sessionId: string }>();

  const [phase, setPhase] = useState<Phase>("ready");
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [evaluation, setEvaluation] = useState<InterviewEvaluation | null>(null);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [textInput, setTextInput] = useState("");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const liveSessionRef = useRef<any>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const recordContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const playingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    Promise.all([
      interviewsApi.get(Number(sessionId)),
      candidatesApi.get(Number(candidateId)),
    ]).then(([sRes, cRes]) => {
      setSession(sRes.data);
      setCandidate(cRes.data);
      if (sRes.data.status === "completed") {
        setPhase("completed");
        setMessages(sRes.data.transcript || []);
        loadEvaluation();
      }
    });
  }, [sessionId, candidateId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadEvaluation() {
    try {
      const res = await interviewsApi.getEvaluation(Number(sessionId));
      setEvaluation(res.data);
    } catch { /* not evaluated yet */ }
  }

  async function startInterview() {
    setPhase("connecting");
    setError("");
    try {
      const cfgRes = await interviewsApi.getConfig(Number(sessionId));
      await connectGeminiLive(cfgRes.data);
    } catch (e: unknown) {
      setError((e as Error).message || "Không thể kết nối. Vui lòng kiểm tra Gemini API Key.");
      setPhase("error");
    }
  }

  async function connectGeminiLive(cfg: GeminiSessionConfig) {
    if (!cfg.gemini_api_key) {
      setError("GEMINI_API_KEY chưa được cấu hình. Vui lòng thêm vào file .env của backend.");
      setPhase("error");
      return;
    }

    const { GoogleGenAI } = await import("@google/genai");
    const ai = new GoogleGenAI({ apiKey: cfg.gemini_api_key });

    const liveSession = await ai.live.connect({
      model: LIVE_MODEL,
      config: {
        // Live API: only AUDIO per session (not both AUDIO+TEXT)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        responseModalities: ["AUDIO"] as any,
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: "Puck" } },
        },
        systemInstruction: { parts: [{ text: cfg.system_prompt }] },
        // Enable transcriptions so we can build a text transcript from audio
        inputAudioTranscription: {},
        outputAudioTranscription: {},
      },
      callbacks: {
        onopen: () => {
          setPhase("interviewing");
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onmessage: async (message: any) => {
          // Setup complete — kick off the interview via sendRealtimeInput (not sendClientContent)
          if (message.setupComplete) {
            setAiSpeaking(true);
            liveSessionRef.current?.sendRealtimeInput({
              text: "Bắt đầu buổi phỏng vấn. Hãy giới thiệu bản thân và bắt đầu.",
            });
            return;
          }

          const content = message.serverContent;
          if (!content) return;

          // Audio chunks from the model — queue for playback
          if (content.modelTurn?.parts) {
            for (const part of content.modelTurn.parts) {
              if (part.inlineData?.mimeType?.startsWith("audio/")) {
                const bytes = Uint8Array.from(atob(part.inlineData.data), c => c.charCodeAt(0));
                audioQueueRef.current.push(bytes.buffer);
                if (!playingRef.current) playAudioQueue();
              }
            }
          }

          // AI speech transcript (streamed incrementally — append to last interviewer bubble)
          if (content.outputTranscription?.text) {
            const chunk: string = content.outputTranscription.text;
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "interviewer") {
                return [...prev.slice(0, -1), { ...last, content: last.content + chunk }];
              }
              return [...prev, { role: "interviewer", content: chunk, timestamp: new Date().toISOString() }];
            });
          }

          // User speech transcript — add as candidate message
          if (content.inputTranscription?.text) {
            const text: string = content.inputTranscription.text;
            setMessages(prev => {
              const last = prev[prev.length - 1];
              if (last?.role === "candidate") {
                return [...prev.slice(0, -1), { ...last, content: last.content + text }];
              }
              return [...prev, { role: "candidate", content: text, timestamp: new Date().toISOString() }];
            });
          }

          // AI finished speaking — start listening
          if (content.turnComplete) {
            setAiSpeaking(false);
            await startMic();
          }

          // Interrupted — clear queued audio immediately
          if (content.interrupted) {
            audioQueueRef.current = [];
            playingRef.current = false;
            setAiSpeaking(false);
          }
        },
        onclose: () => {
          setIsRecording(false);
        },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        onerror: (e: any) => {
          setError("Lỗi kết nối Gemini Live: " + (e?.message || String(e)));
          setPhase("error");
        },
      },
    });

    liveSessionRef.current = liveSession;
  }

  async function playAudioQueue() {
    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext({ sampleRate: 24000 });
    }
    const ctx = playbackContextRef.current;
    playingRef.current = true;
    setAiSpeaking(true);

    while (audioQueueRef.current.length > 0) {
      const buf = audioQueueRef.current.shift()!;
      try {
        const int16 = new Int16Array(buf);
        const float32 = new Float32Array(int16.length);
        for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;
        const audioBuf = ctx.createBuffer(1, float32.length, 24000);
        audioBuf.copyToChannel(float32, 0);
        const source = ctx.createBufferSource();
        source.buffer = audioBuf;
        source.connect(ctx.destination);
        await new Promise<void>(resolve => { source.onended = () => resolve(); source.start(); });
      } catch { /* skip bad chunk */ }
    }
    playingRef.current = false;
    setAiSpeaking(false);
  }

  async function startMic() {
    if (isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
      streamRef.current = stream;
      if (!recordContextRef.current) recordContextRef.current = new AudioContext({ sampleRate: 16000 });
      const ctx = recordContextRef.current;
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!liveSessionRef.current) return;
        const input = e.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) int16[i] = Math.max(-32768, Math.min(32767, input[i] * 32768));
        const bytes = new Uint8Array(int16.buffer);
        let binary = "";
        for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
        const b64 = btoa(binary);
        // Use sendRealtimeInput with audio key (not media)
        liveSessionRef.current.sendRealtimeInput({
          audio: { data: b64, mimeType: "audio/pcm;rate=16000" },
        });
      };

      source.connect(processor);
      processor.connect(ctx.destination);
      setIsRecording(true);
    } catch {
      console.warn("Mic access denied");
    }
  }

  function stopMic() {
    processorRef.current?.disconnect();
    streamRef.current?.getTracks().forEach(t => t.stop());
    // Signal end of audio stream so model can flush cached audio
    liveSessionRef.current?.sendRealtimeInput({ audioStreamEnd: true });
    setIsRecording(false);
  }

  const handleEndInterview = useCallback(async () => {
    setPhase("completing");
    stopMic();
    liveSessionRef.current?.close();

    try {
      await interviewsApi.complete(Number(sessionId), messages);
      await interviewsApi.evaluate(Number(sessionId));
      await loadEvaluation();
      setPhase("completed");
    } catch {
      setPhase("completed");
    }
  }, [messages, sessionId]);

  // Send text as realtime input (not sendClientContent which is only for history seeding)
  async function sendTextMessage(text: string) {
    if (!liveSessionRef.current || !text.trim()) return;
    liveSessionRef.current.sendRealtimeInput({ text: text.trim() });
    setAiSpeaking(true);
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
        <Link href="/jobs" className="hover:text-gray-800">Jobs</Link>
        <span>/</span>
        <Link href={`/jobs/${id}/candidates/${candidateId}`} className="hover:text-gray-800">{candidate?.name}</Link>
        <span>/</span>
        <span className="text-gray-900 font-medium">Phỏng vấn ảo</span>
      </div>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4 flex items-center justify-between">
        <div>
          <h1 className="font-bold text-gray-900">Virtual Interview</h1>
          <p className="text-sm text-gray-500">
            {candidate?.name} · {session ? `Session #${session.id}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {phase === "interviewing" && (
            <>
              <div className={cn("flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full", aiSpeaking ? "bg-blue-50 text-blue-700" : isRecording ? "bg-green-50 text-green-700" : "bg-gray-50 text-gray-500")}>
                <div className={cn("w-2 h-2 rounded-full animate-pulse", aiSpeaking ? "bg-blue-500" : isRecording ? "bg-green-500" : "bg-gray-300")} />
                {aiSpeaking ? "AI đang nói..." : isRecording ? "Đang nghe..." : "Chờ..."}
              </div>
              <button onClick={handleEndInterview} className="px-3 py-1.5 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700">
                Kết thúc
              </button>
            </>
          )}
        </div>
      </div>

      {/* Ready state */}
      {phase === "ready" && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Sẵn sàng phỏng vấn</h2>
          <p className="text-gray-500 mb-6 max-w-sm mx-auto">AI Interviewer sẽ hỏi ứng viên dựa trên JD và CV. Cần quyền truy cập microphone.</p>
          <button onClick={startInterview} className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-indigo-700 flex items-center gap-2 mx-auto">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            </svg>
            Bắt đầu phỏng vấn
          </button>
        </div>
      )}

      {/* Connecting */}
      {phase === "connecting" && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Đang kết nối Gemini Live API...</p>
        </div>
      )}

      {/* Error */}
      {phase === "error" && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p className="text-red-600 font-medium mb-2">Lỗi kết nối</p>
          <p className="text-red-500 text-sm mb-4">{error}</p>
          <button onClick={() => setPhase("ready")} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">
            Thử lại
          </button>
        </div>
      )}

      {/* Interviewing */}
      {phase === "interviewing" && (
        <div className="flex flex-col gap-4">
          <div className="bg-white rounded-xl border border-gray-200 h-96 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-center text-gray-400 py-8">Đang chờ AI bắt đầu...</div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={cn("flex gap-3", msg.role === "interviewer" ? "" : "flex-row-reverse")}>
                <div className={cn("w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium shrink-0 mt-0.5", msg.role === "interviewer" ? "bg-indigo-100 text-indigo-700" : "bg-green-100 text-green-700")}>
                  {msg.role === "interviewer" ? "AI" : "C"}
                </div>
                <div className={cn("max-w-[80%] px-3 py-2 rounded-xl text-sm", msg.role === "interviewer" ? "bg-gray-100 text-gray-800" : "bg-indigo-600 text-white")}>
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Text fallback */}
          <div className="bg-white rounded-xl border border-gray-200 p-3 flex gap-2">
            <input
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") { sendTextMessage(textInput); setTextInput(""); } }}
              placeholder="Hoặc nhập câu trả lời bằng văn bản..."
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={() => { sendTextMessage(textInput); setTextInput(""); }}
              className="px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700"
            >
              Gửi
            </button>
          </div>
        </div>
      )}

      {/* Completing */}
      {phase === "completing" && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
          <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Đang lưu và đánh giá buổi phỏng vấn...</p>
        </div>
      )}

      {/* Completed */}
      {phase === "completed" && (
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
            <p className="text-green-700 font-medium">Phỏng vấn hoàn thành!</p>
          </div>

          {evaluation && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="font-bold text-gray-900 text-lg mb-4">Kết quả đánh giá</h2>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="col-span-2 text-center p-4 bg-gray-50 rounded-xl">
                  <p className={cn("text-5xl font-bold mb-1", getScoreColor(evaluation.overall_score))}>
                    {evaluation.overall_score.toFixed(0)}
                  </p>
                  <p className="text-gray-500 text-sm">Overall Interview Score</p>
                  <p className="text-indigo-600 font-medium mt-1">{evaluation.recommendation}</p>
                </div>
                {[
                  { label: "Technical Knowledge", val: evaluation.technical_knowledge },
                  { label: "Communication", val: evaluation.communication_skills },
                  { label: "Problem Solving", val: evaluation.problem_solving },
                  { label: "Confidence", val: evaluation.confidence },
                  { label: "Role Fit", val: evaluation.role_fit },
                ].map(({ label, val }) => (
                  <div key={label} className="p-3 bg-gray-50 rounded-lg">
                    <p className={cn("text-2xl font-bold", getScoreColor(val))}>{val.toFixed(0)}</p>
                    <p className="text-xs text-gray-500">{label}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <h4 className="font-medium text-gray-800 mb-2 text-sm">Điểm mạnh</h4>
                  <ul className="space-y-1">
                    {evaluation.strengths.map((s, i) => <li key={i} className="text-sm text-gray-600">✓ {s}</li>)}
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-800 mb-2 text-sm">Điểm cần cải thiện</h4>
                  <ul className="space-y-1">
                    {evaluation.weaknesses.map((w, i) => <li key={i} className="text-sm text-gray-600">• {w}</li>)}
                  </ul>
                </div>
              </div>

              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-gray-800 mb-1 text-sm">AI Summary</h4>
                <p className="text-sm text-gray-600 leading-relaxed">{evaluation.summary}</p>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <Link href={`/jobs/${id}/candidates/${candidateId}`} className="flex-1 text-center bg-white border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 text-sm">
              Quay lại hồ sơ
            </Link>
            <Link href={`/jobs/${id}/candidates`} className="flex-1 text-center bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 text-sm">
              Danh sách ứng viên
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
