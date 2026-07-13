import { redirect } from "next/navigation";

const PRODUCTION_ADMIN_URL = "https://venusrealm.net/admin?page=command-center";

export default function AdminRedirect() {
  redirect(process.env.ADMIN_DASHBOARD_URL || PRODUCTION_ADMIN_URL);
}
