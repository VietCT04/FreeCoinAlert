"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { InlineError } from "@/components/inline-error";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AuthApiError, signIn } from "./api";
import { AuthShell } from "./auth-shell";
import { useAuth } from "./auth-provider";

function getSignInError(error: unknown): string {
  if (error instanceof AuthApiError) {
    if (error.code === "AUTH_INVALID_CREDENTIALS") {
      return "Email or password is incorrect.";
    }

    if (error.status === 429 || error.code === "AUTH_RATE_LIMITED") {
      return "Too many sign-in attempts. Please wait and try again.";
    }
  }

  return "We couldn't sign you in. Please try again.";
}

export function SignInForm() {
  const router = useRouter();
  const { setAuthenticatedSession, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [router, status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (isSubmitting) {
      return;
    }

    if (!email) {
      setError("Enter your email address.");
      return;
    }

    if (!password) {
      setError("Enter your password.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      setAuthenticatedSession(await signIn(email, password));
      router.replace("/dashboard");
    } catch (requestError) {
      setError(getSignInError(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      description="Sign in to manage your informational market alerts."
      footer={
        <>
          Need an account?{" "}
          <Link className="font-medium text-foreground underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" href="/sign-up">
            Sign up
          </Link>
        </>
      }
      title="Sign in"
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="sign-in-email">Email</Label>
          <Input
            autoComplete="email"
            id="sign-in-email"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="sign-in-password">Password</Label>
          <Input
            autoComplete="current-password"
            id="sign-in-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </div>
        {error ? (
          <InlineError message={error} title="Sign-in failed" />
        ) : (
          <p aria-live="polite" className="sr-only" />
        )}
        <Button
          aria-busy={isSubmitting}
          className="w-full"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
