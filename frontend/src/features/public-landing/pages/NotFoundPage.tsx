import { Link } from "react-router-dom";
import { Stack, Button } from "@/shared/components";
import { useTranslation } from "react-i18next";

export const NotFoundPage = () => {
  const { t } = useTranslation();
  return (
    <div className="flex-grow flex items-center justify-center">
      <Stack className="gap-4 text-center items-center">
        <h1 className="text-xl font-bold">{t("notFound.title")}</h1>
        <p className="text-md text-muted-foreground">{t("notFound.message")}</p>
        <Link to="/" className="mt-4 contents">
          <Button variant="secondary">{t("notFound.home")}</Button>
        </Link>
      </Stack>
    </div>
  );
};
