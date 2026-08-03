"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { AuthApiError, registerAccount } from "./api";
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
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 py-16 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50">
      <section className="w-full max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-sm ring-1 ring-zinc-200 dark:bg-zinc-900 dark:ring-zinc-800">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Create an account</h1>
          <p className="text-zinc-600 dark:text-zinc-300">
            Start with a secure FreeCoinAlert account.
          </p>
        </div>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              autoComplete="email"
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
              id="email"
              name="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="password">
              Password
            </label>
            <input
              autoComplete="new-password"
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
              id="password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium" htmlFor="confirm-password">
              Confirm password
            </label>
            <input
              autoComplete="new-password"
              className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-50"
              id="confirm-password"
              name="confirm-password"
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              type="password"
              value={confirmPassword}
            />
          </div>
          <p aria-live="polite" className="min-h-6 text-sm text-red-700 dark:text-red-300">
            {error}
          </p>
          <button
            className="w-full rounded-lg bg-zinc-900 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-60 dark:bg-zinc-50 dark:text-zinc-900"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          Already have an account?{" "}
          <Link className="font-medium underline" href="/sign-in">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
