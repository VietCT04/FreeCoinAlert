import type { ReactNode } from "react";
import { useId } from "react";

import { cn } from "@/lib/utils";

type ResponsiveTableProps = {
  caption?: string;
  children: ReactNode;
  className?: string;
};

export function ResponsiveTable({
  caption,
  children,
  className,
}: ResponsiveTableProps) {
  const captionId = `responsive-table-caption-${useId().replace(/:/g, "")}`;

  return (
    <div
      aria-describedby={caption ? captionId : undefined}
      className={cn("relative w-full overflow-x-auto", className)}
      role="region"
      tabIndex={0}
    >
      {caption ? (
        <p className="sr-only" id={captionId}>
          {caption}
        </p>
      ) : null}
      {children}
    </div>
  );
}
