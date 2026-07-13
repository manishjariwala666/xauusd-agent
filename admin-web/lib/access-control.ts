export const PUBLIC_ADMIN_PATHS = new Set(["/admin/login", "/admin/forbidden"]);

export function isProtectedAdminPath(pathname: string): boolean {
  return pathname === "/admin" || (
    pathname.startsWith("/admin/") && !PUBLIC_ADMIN_PATHS.has(pathname)
  );
}
