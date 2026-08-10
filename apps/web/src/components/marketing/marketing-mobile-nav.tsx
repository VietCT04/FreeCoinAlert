"use client";

import Link from "next/link";
import { MenuIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

const primaryLinks = [
  { href: "/crypto-backtesting", label: "Backtest" },
  { href: "/strategy-alerts", label: "Alerts" },
  { href: "/guides", label: "Guides" },
] as const;

export function MarketingMobileNav() {
  return (
    <div className="md:hidden">
      <Sheet>
        <SheetTrigger asChild>
          <Button aria-label="Open navigation" size="icon" variant="ghost">
            <MenuIcon aria-hidden="true" />
          </Button>
        </SheetTrigger>
        <SheetContent className="w-[min(88vw,22rem)]" side="right">
          <SheetHeader>
            <SheetTitle>FreeCoinAlert navigation</SheetTitle>
          </SheetHeader>
          <nav aria-label="Mobile marketing navigation" className="px-4">
            <div className="grid gap-1">
              {primaryLinks.map(({ href, label }) => (
                <SheetClose asChild key={href}>
                  <Link
                    className="rounded-lg px-3 py-2.5 text-base font-medium text-foreground outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                    href={href}
                  >
                    {label}
                  </Link>
                </SheetClose>
              ))}
            </div>
            <div className="mt-5 grid gap-1 border-t pt-5">
              <SheetClose asChild>
                <Link
                  className="rounded-lg px-3 py-2.5 text-base font-medium text-foreground outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                  href="/sign-in"
                >
                  Sign in
                </Link>
              </SheetClose>
              <SheetClose asChild>
                <Button asChild className="mt-2 w-full">
                  <Link href="/sign-up">Start free</Link>
                </Button>
              </SheetClose>
            </div>
          </nav>
        </SheetContent>
      </Sheet>
    </div>
  );
}
