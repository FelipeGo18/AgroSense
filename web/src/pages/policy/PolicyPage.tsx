import { Link } from "react-router";
import { PATHS } from "@/app/paths";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Mascot } from "@/components/mascot/Mascot";
import { Card } from "@/components/ui/Card";
import { CONSENT_VERSION, useSession } from "@/features/auth/session";
import { LEGAL_REVIEW_PENDING, POLICY_SINCE, SECTIONS, type Mark } from "./content";

const LINK = "font-bold text-oscuro-oliva underline decoration-2 underline-offset-4";

/** La marca de cada frase, con forma y no solo color: visto bueno (se guarda), equis (nunca) o una flecha (explica). */
function ItemMark({ mark }: { mark: Mark }) {
  if (mark === "note") {
    return (
      <svg aria-hidden="true" viewBox="0 0 22 22" className="mt-0.5 size-[22px] shrink-0">
        <polygon points="7,5 16,11 7,17" fill="var(--color-paleta-calabaza)" />
      </svg>
    );
  }
  const kept = mark === "kept";
  const stroke = kept ? "var(--color-oscuro-oliva)" : "var(--color-oscuro-rojo)";
  return (
    <svg aria-hidden="true" viewBox="0 0 22 22" className="mt-0.5 size-[22px] shrink-0">
      <rect x="1" y="1" width="20" height="20" rx={kept ? 4 : 0} fill={kept ? "#E9F2D8" : "#FBE6E2"} stroke={stroke} strokeWidth="2" />
      {kept ? (
        <polyline points="5,11 9,16 17,6" fill="none" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      ) : (
        <path d="M6 6l10 10M16 6L6 16" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      )}
    </svg>
  );
}

/** Lo que la marca dice, para quien no la ve. */
const MARK_TEXT: Record<Mark, string> = { kept: "Se guarda: ", never: "No se guarda: ", note: "" };

/**
 * Política de tratamiento de datos (HU-163). Se puede leer sin cuenta: a ella llevan el consentimiento de «Crear
 * cuenta», «Lo que guardamos de usted» de Mi cuenta y el pie de página. Diseño: design/pantallas/politica.py.
 * Es una página quieta: no tiene nada que animar, así que se ve igual en modo ligero.
 */
export function PolicyPage() {
  const { user } = useSession();
  return (
    <div className="min-h-svh bg-paleta-niebla">
      <title>Política de tratamiento de datos · AgroSense</title>
      <TopBar />
      {/* El espacio de abajo es para los cerros del pie de página. */}
      <main className="container-page pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        <div className="flex items-start justify-between gap-8">
          <header className="flex max-w-[880px] min-w-0 flex-col gap-3">
            <h1 className="text-[clamp(1.75rem,4vw,3rem)]">Política de tratamiento de datos</h1>
            <p className="text-texto-secundario">
              Versión {CONSENT_VERSION} · vigente desde el {POLICY_SINCE}
            </p>
            <p>Lo que guardamos de usted, para qué y cómo borrarlo. Sin cuenta no se guarda nada de su finca.</p>
          </header>
          <Mascot mood="guide" decorative className="hidden h-auto w-[200px] lg:block" />
        </div>

        {LEGAL_REVIEW_PENDING && (
          <p role="note" className="mt-6 max-w-[880px] border-l-8 border-paleta-calabaza bg-superficie-panel px-4 py-3 font-bold">
            Este texto todavía necesita revisión legal. Dice lo que AgroSense hace hoy con sus datos; la redacción puede cambiar cuando un
            abogado la revise.
          </p>
        )}

        <div className="mt-6 max-w-[880px]">
          <Card bodyClassName="gap-0 md:px-4 md:pt-2">
            {SECTIONS.map((section, i) => (
              <section key={section.title} className={`flex flex-col gap-3 py-5 ${i ? "border-t-2 border-paleta-niebla" : "pt-1"}`}>
                <h2 className="text-[clamp(1.25rem,2.4vw,1.625rem)]">{section.title}</h2>
                <ul className="flex flex-col gap-3">
                  {section.items.map((item) => (
                    <li key={item.text} className="flex gap-3">
                      <ItemMark mark={item.mark} />
                      <span className="min-w-0">
                        <span className="sr-only">{MARK_TEXT[item.mark]}</span>
                        {item.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </Card>
        </div>

        <p className="mt-8 max-w-[880px]">Responde por estos datos el equipo RealE4Life, que hace AgroSense.</p>
        <p className="mt-4 flex flex-wrap gap-x-8 gap-y-3">
          {user ? (
            <Link to={PATHS.account} className={`${LINK} inline-flex min-h-11 items-center`}>
              Ir a Mi cuenta
            </Link>
          ) : (
            <>
              <Link to={PATHS.signup} className={`${LINK} inline-flex min-h-11 items-center`}>
                Crear cuenta
              </Link>
              <Link to={PATHS.login} className={`${LINK} inline-flex min-h-11 items-center`}>
                Entrar
              </Link>
            </>
          )}
        </p>
      </main>
      <Footer />
    </div>
  );
}
