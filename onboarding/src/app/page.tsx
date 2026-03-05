import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome to BioIntelligence</CardTitle>
          <CardDescription>
            Complete your health profile to receive personalised, evidence-based
            daily insights powered by your Garmin data.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            The onboarding takes about 3 minutes for essential fields. You can
            skip optional sections and complete them later.
          </p>
          <Link href="/onboarding/step-1" className="w-full">
            <Button className="w-full" size="lg">
              Start Onboarding
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
