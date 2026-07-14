import {NextRequest} from "next/server";import {publicationProxy} from "@/lib/publication-bff";
export const GET=(r:NextRequest)=>publicationProxy(r,"results");export const POST=(r:NextRequest)=>publicationProxy(r,"results");
