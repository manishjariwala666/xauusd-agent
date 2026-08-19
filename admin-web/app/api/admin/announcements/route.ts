import {NextRequest} from "next/server";import {publicationProxy} from "@/lib/publication-bff";
export const GET=(r:NextRequest)=>publicationProxy(r,"announcements");export const POST=(r:NextRequest)=>publicationProxy(r,"announcements");
