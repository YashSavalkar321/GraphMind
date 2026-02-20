import { CheckCircle2, AlertCircle } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Toast() {
  const toast = useAppStore((s) => s.toast);
  if (!toast) return null;

  const isSuccess = toast.type === 'success';

  return (
    <div className="fixed bottom-6 right-6 z-[100] animate-fade-in pointer-events-none">
      <div
        className={`flex items-center gap-3 px-5 py-3.5 rounded-xl border shadow-2xl shadow-black/40 backdrop-blur-lg ${
          isSuccess
            ? 'bg-success/15 border-success/25 text-success'
            : 'bg-danger/15 border-danger/25 text-danger'
        }`}
      >
        {isSuccess ? (
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
        ) : (
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
        )}
        <span className="text-sm font-medium">{toast.message}</span>
      </div>
    </div>
  );
}
