import type { Metadata } from "next";
import { AccessPage } from "@/components/access-page";
export const metadata: Metadata = { title: "Reset Password" };
export default function ResetPasswordPage() { return <AccessPage mode="reset" />; }
