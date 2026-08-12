import { NextRequest } from "next/server";import { leadProxy } from "@/lib/lead-bff";
export const GET=(request:NextRequest)=>leadProxy(request);
