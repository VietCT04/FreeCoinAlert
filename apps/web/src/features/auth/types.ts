export type AuthUser = {
  id: string;
  email: string;
  createdAt: string;
};

export type AuthenticationResponse = {
  user: AuthUser;
  csrfToken: string;
};

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";
