import type { Metadata } from "next";

import { SignInForm } from "../../features/auth/sign-in-form";
import { createPrivateMetadata } from "../../lib/seo/metadata";

export const metadata: Metadata = createPrivateMetadata({
  title: "Sign in",
  description:
    "Sign in to manage your FreeCoinAlert alerts and subscriptions.",
});

export default function SignInPage() {
  return <SignInForm />;
}
