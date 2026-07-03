import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import useAppStore from '../store/useAppStore';

export default function Toast() {
  const toast = useAppStore((s) => s.toast);

  return (
    <AnimatePresence>
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 24, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 12, scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 380, damping: 28 }}
          className="fixed bottom-6 right-6 z-[100] pointer-events-none"
        >
          <div
            className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl glass-strong ${
              toast.type === 'success'
                ? '!border-success/35 shadow-[0_0_30px_rgba(52,211,153,0.2),0_24px_70px_-12px_rgba(0,0,0,0.7)]'
                : '!border-danger/35 shadow-[0_0_30px_rgba(248,113,113,0.2),0_24px_70px_-12px_rgba(0,0,0,0.7)]'
            }`}
          >
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${
                toast.type === 'success' ? 'bg-success/15' : 'bg-danger/15'
              }`}
            >
              {toast.type === 'success' ? (
                <CheckCircle2 className="w-4.5 h-4.5 text-success" />
              ) : (
                <AlertCircle className="w-4.5 h-4.5 text-danger" />
              )}
            </div>
            <span className="text-sm font-medium text-text-primary">{toast.message}</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
