import { redirect } from "next/navigation";
export default function AdminRedirect() { redirect(process.env.ADMIN_DASHBOARD_URL || "https://admin.venusrealm.net"); }
