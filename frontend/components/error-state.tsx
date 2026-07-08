import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

type ErrorStateProps = {
  message: string;
  onRetry?: () => void;
};

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="rounded-md border border-coral/30 bg-[#fff3f0] p-4 text-sm text-ink shadow-soft">
      <p className="font-semibold">{message}</p>
      <p className="mt-1 text-[#6f544d]">Check your connection and try again.</p>
      {onRetry ? (
        <Button className="mt-3" type="button" variant="secondary" onClick={onRetry}>
          <RotateCcw size={16} aria-hidden="true" />
          Retry
        </Button>
      ) : null}
    </div>
  );
}
