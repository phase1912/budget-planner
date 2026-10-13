import { Link } from "react-router-dom";
import { Button } from "@/shared/components";
import { Camera, ArrowRight } from "lucide-react";
import { useTranslation } from "react-i18next";

export const PublicLandingPage = () => {
  const { t } = useTranslation("landing");
  return (
    <div className="flex-grow flex flex-col items-center justify-center py-8">
      <div className="max-w-[720px] flex flex-col items-center gap-8 text-center">
        <div className="w-[72px] h-[72px] rounded-full bg-tone-primary-bg text-tone-primary-text flex items-center justify-center">
          <Camera size={34} strokeWidth={1.7} />
        </div>

        <div className="flex flex-col gap-4">
          <h1 className="text-4xl leading-[1.15] font-bold">
            {t("title1")}
            <br />
            {t("title2")}
          </h1>
          <p className="text-[17px] leading-[1.6] text-muted-foreground max-w-[560px] mx-auto text-pretty">
            {t("lead")}
          </p>
        </div>

        <div className="flex items-center gap-3 mt-2">
          <Link to="/register" className="contents">
            <Button size="lg" className="text-[15px]">
              {t("createAccount")}
              <ArrowRight size={17} className="ml-2" />
            </Button>
          </Link>
          <Link to="/login" className="contents">
            <Button variant="secondary" size="lg" className="text-[15px]">
              {t("haveOne")}
            </Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full border-t border-border pt-8 mt-4 text-left">
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              1
            </div>
            <span className="text-[14px] font-semibold">{t("steps.shoot.title")}</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              {t("steps.shoot.text")}
            </span>
          </div>
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              2
            </div>
            <span className="text-[14px] font-semibold">{t("steps.check.title")}</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              {t("steps.check.text")}
            </span>
          </div>
          <div className="flex flex-col gap-[10px]">
            <div className="w-[26px] h-[26px] rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[12px] font-bold">
              3
            </div>
            <span className="text-[14px] font-semibold">{t("steps.see.title")}</span>
            <span className="text-[13px] text-muted-foreground leading-relaxed">
              {t("steps.see.text")}
            </span>
          </div>
        </div>
      </div>

      <footer className="mt-auto pt-16 pb-4 w-full text-center border-t border-border/50">
        <p className="text-sm text-muted-foreground">{t("privacy")}</p>
      </footer>
    </div>
  );
};
