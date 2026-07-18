import type { Metadata } from "next";
import { AccessPage } from "@/components/access-page";
export const metadata: Metadata = { title: "Signup" };
export default function SignupPage() { return <AccessPage mode="signup" />; }
