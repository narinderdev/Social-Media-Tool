import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

const toastIcons = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info
};

function ToastStack({ toasts, onDismiss }) {
  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => {
        const Icon = toastIcons[toast.type] || Info;
        return (
          <section className={`toast ${toast.type}`} key={toast.id}>
            <Icon size={18} />
            <p>{toast.message}</p>
            <button type="button" onClick={() => onDismiss(toast.id)} aria-label="Dismiss toast">
              <X size={15} />
            </button>
          </section>
        );
      })}
    </div>
  );
}

export default ToastStack;
