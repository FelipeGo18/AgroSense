import { t } from "@/lib/i18n";
import { useTranslation } from "react-i18next";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

/** Lugar al que llegan los enlaces de una pantalla que ya está diseñada pero todavía no se programó. */
export function PendingPage({ title }: { title: string }) {
  useTranslation();
  return (
    <>
      <title>{t("pending.pageTitle", { title: t(title) })}</title>
      <TopBar />
      <main className="mx-auto flex min-h-svh max-w-2xl flex-col justify-center px-5 pt-28 pb-40 md:pb-48">
        {/* El espacio de abajo es para los cerros del pie de página. */}
        <Card>
          <Mascot mood="idle" size={150} lively decorative className="self-center" />
          <h1 className="text-2xl">{t(title)}</h1>
          <p>{t("pages.pending.PendingPage.thisScreenHasBeenDesignedButIs")}</p>
          <ButtonLink to={PATHS.home} className="self-start">
            {t("pages.pending.PendingPage.backToHome")}
          </ButtonLink>
        </Card>
      </main>
      <Footer />
    </>
  );
}
