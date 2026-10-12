import { PATHS } from "@/app/paths";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot } from "@/components/mascot/Mascot";
import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function NotFoundPage() {
  return (
    <>
      <TopBar />
      <main className="mx-auto flex min-h-svh max-w-2xl flex-col justify-center px-5 pt-28 pb-16">
        <Card>
          <Mascot mood="no_data" size={150} decorative className="self-center" />
          <h1 className="text-2xl">Esta dirección no existe</h1>
          <p>Revise la dirección o vuelva al inicio.</p>
          <ButtonLink to={PATHS.home} className="self-start">
            Volver al inicio
          </ButtonLink>
        </Card>
      </main>
    </>
  );
}
