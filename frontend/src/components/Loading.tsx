export function Loading({ label = 'Đang tải…' }: { label?: string }) {
  return <div className="flex items-center justify-center gap-3 py-14 text-sm text-[#74867e]" role="status"><span className="size-5 animate-spin rounded-full border-2 border-[#c9ddd1] border-t-[#28765c]" />{label}</div>
}
