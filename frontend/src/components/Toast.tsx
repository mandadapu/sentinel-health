import { useEffect, useState } from "react";

type ToastType = "success" | "error" | "info";

interface ToastState {
  message: string;
  type: ToastType;
  id: number;
}

let addToast: (message: string, type?: ToastType) => void = () => {};

export function toast(message: string, type: ToastType = "info") {
  addToast(message, type);
}

const typeStyles: Record<ToastType, string> = {
  success: "bg-green-600",
  error: "bg-red-600",
  info: "bg-gray-800",
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastState[]>([]);

  useEffect(() => {
    addToast = (message: string, type: ToastType = "info") => {
      const id = Date.now();
      setToasts((prev) => [...prev, { message, type, id }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4000);
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${typeStyles[t.type]} rounded-lg px-4 py-3 text-sm text-white shadow-lg transition-opacity`}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
