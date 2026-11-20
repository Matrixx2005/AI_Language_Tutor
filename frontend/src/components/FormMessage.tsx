import { AlertCircle } from 'lucide-react'

export function FormMessage({ children }: { children: React.ReactNode }) {
  return <div role="alert" className="flex items-start gap-2 rounded-xl border border-[#f1d0c8] bg-[#fff5f2] px-4 py-3 text-sm text-[#a14f3d]"><AlertCircle size={17} className="mt-0.5 shrink-0" />{children}</div>
}

export function FieldError({ children }: { children?: string }) {
  return children ? <p className="mt-1.5 text-xs text-[#a14f3d]">{children}</p> : null
}
