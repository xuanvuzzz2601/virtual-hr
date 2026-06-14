"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearAuth, getUser } from "@/lib/auth";
import { User } from "@/types";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/jobs", label: "Job Descriptions" },
];

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    setUser(getUser());
  }, []);

  function handleLogout() {
    clearAuth();
    router.push("/login");
  }

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-8">
        <Link href="/jobs" className="flex items-center gap-2">
          <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <span className="font-bold text-gray-900 text-sm">Virtual HR</span>
        </Link>

        <div className="flex items-center gap-1">
          {navLinks.map(link => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
                pathname.startsWith(link.href)
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100"
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-900">{user.name}</p>
              <p className="text-xs text-gray-500 capitalize">{user.role.replace("_", " ")}</p>
            </div>
            <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-indigo-700">
                {user.name.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-800 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
        >
          Đăng xuất
        </button>
      </div>
    </nav>
  );
}
