import type { Metadata } from "next";
import { AccessPage } from "@/components/access-page";

export const metadata: Metadata = { title: "Verify Email" };
export default function VerifyEmailPage() { return <AccessPage mode="verify" />; }
