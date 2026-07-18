import type { Metadata } from "next";
import { AccessPage } from "@/components/access-page";
export const metadata: Metadata = { title: "Login" };
export default function LoginPage() { return <AccessPage mode="login" />; }
