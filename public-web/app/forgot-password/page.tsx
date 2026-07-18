import type { Metadata } from "next";
import { AccessPage } from "@/components/access-page";
export const metadata: Metadata = { title: "Forgot Password" };
export default function ForgotPasswordPage() { return <AccessPage mode="forgot" />; }
