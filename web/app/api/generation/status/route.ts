import { readGenerationStatus } from "@/lib/generation-env";

export async function GET() {
  return Response.json(readGenerationStatus());
}
