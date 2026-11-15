import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function NotFoundPage() {
  useTranslation();
  return (
    <>
      <title>{t("pending.notFoundTitle")}</title>
      <TopBar />
      <main className="mx-auto flex min-h-svh max-w-2xl flex-col justify-center px-5 pt-28 pb-40 md:pb-48">
        {/* El espacio de abajo es para los cerros del pie de página. */}
        <Card>
          <Mascot mood="no_data" size={150} decorative className="self-center" />
          <h1 className="text-2xl">{t("pages.pending.NotFoundPage.thisPageDoesNotExist")}</h1>
          <p>{t("pages.pending.NotFoundPage.checkTheAddressOrReturnToThe")}</p>
          <ButtonLink to={PATHS.home} className="self-start">
            {t("pages.pending.PendingPage.backToHome")}
          </ButtonLink>
        </Card>
      </main>
      <Footer />
    </>
  );
}
