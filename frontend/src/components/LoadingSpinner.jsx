export default function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary/25 to-accent/20 blur-lg animate-breathe" />
        <div className="orb-ring" style={{ animationDuration: '1.4s' }} />
        <div className="absolute inset-[6px] rounded-full bg-[#0a0d1d]" />
      </div>
      <p className="text-sm text-text-secondary">{message}</p>
    </div>
  );
}
