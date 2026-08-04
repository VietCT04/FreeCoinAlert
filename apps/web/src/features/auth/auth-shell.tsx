import Link from "next/link";
import type { ReactNode } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";

type AuthShellProps = {
  children: ReactNode;
  description: string;
  footer: ReactNode;
  title: string;
};

export function AuthShell({
  children,
  description,
  footer,
  title,
}: AuthShellProps) {
  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/30 px-4 py-10 sm:px-6 sm:py-16">
      <div className="w-full max-w-md space-y-6">
        <Link
          className="mx-auto flex w-fit items-center gap-2 text-sm font-semibold tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          href="/"
        >
          <span
            aria-hidden="true"
            className="flex size-8 items-center justify-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground"
          >
            FC
          </span>
          FreeCoinAlert
        </Link>
        <Card>
          <CardHeader>
            <h1 className="font-heading text-2xl leading-snug font-medium">
              {title}
            </h1>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>{children}</CardContent>
          <CardFooter className="justify-center text-sm text-muted-foreground">
            {footer}
          </CardFooter>
        </Card>
      </div>
    </main>
  );
}
