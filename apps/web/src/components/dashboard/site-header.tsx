"use client";

import Link from "next/link";
import { LogOut, UserCircle } from "lucide-react";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

import { getDashboardRoute } from "./routes";

type SiteHeaderProps = {
  isSigningOut: boolean;
  onSignOut: () => void;
  userEmail: string;
};

export function SiteHeader({
  isSigningOut,
  onSignOut,
  userEmail,
}: SiteHeaderProps) {
  const pathname = usePathname();
  const route = getDashboardRoute(pathname ?? "/dashboard");

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-4 backdrop-blur md:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <SidebarTrigger aria-label="Open navigation" />
        <Separator className="mx-1 h-4" orientation="vertical" />
        <Breadcrumb>
          <BreadcrumbList>
            {route.href === "/dashboard" ? (
              <BreadcrumbItem>
                <BreadcrumbPage>{route.label}</BreadcrumbPage>
              </BreadcrumbItem>
            ) : (
              <>
                <BreadcrumbItem className="hidden sm:inline-flex">
                  <BreadcrumbLink asChild>
                    <Link href="/dashboard">Overview</Link>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden sm:inline-flex" />
                <BreadcrumbItem>
                  <BreadcrumbPage>{route.label}</BreadcrumbPage>
                </BreadcrumbItem>
              </>
            )}
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <ThemeToggle />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              aria-label="Open account menu"
              className="max-w-[min(18rem,45vw)] justify-start"
              size="sm"
              type="button"
              variant="outline"
            >
              <UserCircle aria-hidden="true" />
              <span className="truncate">{userEmail}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="max-w-56 truncate">
              {userEmail}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              disabled={isSigningOut}
              onSelect={(event) => {
                event.preventDefault();
                onSignOut();
              }}
            >
              <LogOut aria-hidden="true" />
              {isSigningOut ? "Signing out…" : "Sign out"}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
