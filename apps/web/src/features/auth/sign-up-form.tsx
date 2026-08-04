"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { InlineError } from "@/components/inline-error";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AuthApiError, registerAccount } from "./api";
import { AuthShell } from "./auth-shell";
import { useAuth } from "./auth-provider";

function getSignUpError(error: unknown): string {
  if (error instanceof AuthApiError) {
    if (error.code === "AUTH_REGISTRATION_UNAVAILABLE") {
      return "An account cannot be created with these details. Try signing in or use a different email.";
    }

    if (error.status === 429 || error.code === "AUTH_RATE_LIMITED") {
      return "Too many account attempts. Please wait and try again.";
    }
  }

  return "We couldn't create your account. Please try again.";
}

function getPasswordValidationError(
  password: string,
  confirmPassword: string,
): string | null {
  const passwordLength = Array.from(password).length;

  if (passwordLength < 15 || passwordLength > 128) {
    return "Password must be between 15 and 128 characters.";
  }

  if (password !== confirmPassword) {
    return "Passwords must match.";
  }

  return null;
}

export function SignUpForm() {
  const router = useRouter();
  const { setAuthenticatedSession, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
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

    const passwordValidationError = getPasswordValidationError(
      password,
      confirmPassword,
    );

    if (passwordValidationError) {
      setError(passwordValidationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      setAuthenticatedSession(await registerAccount(email, password));
      router.replace("/dashboard");
    } catch (requestError) {
      setError(getSignUpError(requestError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthShell
      description="Create an account to manage your informational market alerts."
      footer={
        <>
          Already have an account?{" "}
          <Link className="font-medium text-foreground underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" href="/sign-in">
            Sign in
          </Link>
        </>
      }
      title="Create an account"
    >
      <form className="space-y-5" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <Label htmlFor="sign-up-email">Email</Label>
          <Input
            autoComplete="email"
            id="sign-up-email"
            name="email"
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="sign-up-password">Password</Label>
          <Input
            autoComplete="new-password"
            id="sign-up-password"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          <p className="text-xs text-muted-foreground">
            Use 15–128 characters.
          </p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="sign-up-confirm-password">Confirm password</Label>
          <Input
            autoComplete="new-password"
            id="sign-up-confirm-password"
            name="confirm-password"
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            type="password"
            value={confirmPassword}
          />
        </div>
        {error ? (
          <InlineError message={error} title="Account creation failed" />
        ) : (
          <p aria-live="polite" className="sr-only" />
        )}
        <Button
          aria-busy={isSubmitting}
          className="w-full"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
