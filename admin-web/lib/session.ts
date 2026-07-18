export const ADMIN_SESSION_COOKIE = "vr_admin_session";
export const ADMIN_CSRF_COOKIE = "vr_admin_csrf";
export const ADMIN_SESSION_MAX_AGE_SECONDS = 15 * 60;

export function sessionCookieOptions(maxAge = ADMIN_SESSION_MAX_AGE_SECONDS) {
  return {
    httpOnly: true,
    secure: true,
    sameSite: "lax" as const,
    path: "/",
    maxAge: Math.max(0, Math.min(maxAge, ADMIN_SESSION_MAX_AGE_SECONDS))
  };
}

export function csrfCookieOptions() {
  return {
    httpOnly: true,
    secure: true,
    sameSite: "lax" as const,
    path: "/",
    maxAge: 10 * 60
  };
}
