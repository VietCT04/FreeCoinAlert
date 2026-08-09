import type { Metadata } from "next";

import { SignUpForm } from "../../features/auth/sign-up-form";
import { createPrivateMetadata } from "../../lib/seo/metadata";

export const metadata: Metadata = createPrivateMetadata({
  title: "Create an account",
  description:
    "Create a FreeCoinAlert account to manage alerts and subscriptions.",
});

export default function SignUpPage() {
  return <SignUpForm />;
}
