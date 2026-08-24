import { Link } from "react-router-dom";
import { Button } from "@/shared/components";
import { Camera, ArrowRight } from "lucide-react";

export const PublicLandingPage = () => {
  return (
    <div className="flex-grow flex flex-col items-center justify-center py-8">
      <div className="max-w-[720px] flex flex-col items-center gap-8 text-center">
        <div className="w-[72px] h-[72px] rounded-full bg-tone-success-bg text-tone-success-text flex items-center justify-center">
          <Camera size={34} strokeWidth={1.7} />
        </div>

        <div className="flex flex-col gap-4">
          <h1 className="text-4xl leading-[1.15] font-bold">
            Photograph a receipt.
            <br />
            Get a budget.
          </h1>
          <p className="text-[17px] leading-[1.6] text-muted-foreground max-w-[560px] mx-auto text-pretty">
            Every line item read off the photo, sorted into categories, and totalled by the month it
            was actually bought in.
          </p>
        </div>

        <div className="flex items-center gap-3 mt-2">
          <Link to="/register" className="contents">
            <Button size="lg" className="text-[15px]">
              Create an account
              <ArrowRight size={17} className="ml-2" />
            </Button>
          </Link>
          <Link to="/login" className="contents">
            <Button variant="secondary" size="lg" className="text-[15px]">
              I already have one
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full border-t border-border pt-8 mt-4 text-left">
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              1
            </div>
            <span className="text-[14px] font-semibold">Shoot it</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              One photo, or several overlapping ones for a long receipt.
            </span>
          </div>
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              2
            </div>
            <span className="text-[14px] font-semibold">Check what we read</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              Anything unclear is flagged for you rather than quietly guessed.
            </span>
          </div>
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              3
            </div>
            <span className="text-[14px] font-semibold">See where it went</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              Month-to-date spend by category, against a limit you set.
            </span>
          </div>
        </div>
      </div>

      <footer className="mt-auto pt-16 pb-4 w-full text-center border-t border-border/50">
        <p className="text-sm text-muted-foreground">
          Receipt photos and their extracted data are encrypted at rest and visible only to you.
        </p>
      </footer>
    </div>
  );
};
