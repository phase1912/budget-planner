import { useTranslation } from "react-i18next";

import { Card, CardBody, CardHeader } from "@/shared/components/Card/Card";
import { LanguageSwitcher } from "@/features/language/LanguageSwitcher";

/** The language the app is shown in, on Profile (F9.9); a change applies at once. */
export function LanguageCard() {
  const { t } = useTranslation();
  return (
    <Card variant="surface" flush>
      <CardHeader>{t("language.label")}</CardHeader>
      <CardBody className="flex flex-col items-start justify-between gap-4 md:flex-row md:gap-8">
        <p className="m-0 w-full max-w-sm text-md leading-relaxed text-muted-foreground">
          {t("language.hint")}
        </p>
        <div className="w-full md:w-64 md:flex-shrink-0">
          <LanguageSwitcher />
        </div>
      </CardBody>
    </Card>
  );
}
