import { t, locale } from "@/lib/i18n";
/**
 * El texto de la política de tratamiento de datos (HU-163, R9). Dice, con más detalle, lo mismo que el consentimiento
 * de «Crear cuenta». Misma redacción que el diseño: design/pantallas/politica.py.
 *
 * Cada frase sale de las specs (R9 de specs/01-reglas.md, HU-160 a HU-165, HU-170, HU-178, HU-200 y
 * specs/02-contratos.md): aquí no se promete nada que el sistema no haga. Si cambia lo que se guarda, cambia este
 * texto y sube la versión del consentimiento.
 *
 * **Falta la revisión legal** (Ley 1581 de 2012 de Colombia, decisión 11): la página lo dice mientras
 * `LEGAL_REVIEW_PENDING` sea verdadero. El canal de contacto es «Escribir al responsable» (`/mi-cuenta/escribirnos`, HU-163).
 */

/** Mientras sea verdadero, la página avisa que el texto todavía no pasó por revisión legal. */
export const LEGAL_REVIEW_PENDING = true;

export const POLICY_SINCE = () =>
  new Intl.DateTimeFormat(locale(), { dateStyle: "long", timeZone: "UTC" }).format(new Date("2026-10-11T12:00:00Z"));

/** Qué dice una frase: algo que se guarda, algo que nunca se guarda o una explicación. */
export type Mark = "kept" | "never" | "note";

export const SECTIONS = (): { title: string; items: { mark: Mark; text: string }[] }[] => [
  {
    title: t("pages.policy.content.whatWeStoreWhenYouHaveAn"),
    items: [
      { mark: "kept", text: t("pages.policy.content.yourUsernamePreferredNameAndPriorities") },
      { mark: "kept", text: t("pages.policy.content.yourPlotsNameBoundaryDrawnOnThe") },
      { mark: "kept", text: t("pages.policy.content.yourPlantingsAndHarvestsWithTheDiagnosis") },
      { mark: "kept", text: t("pages.policy.content.yourActiveSessionsSoYouCanSign") },
      { mark: "kept", text: t("pages.policy.content.yourAccountActivityFor180DaysWhat") },
      { mark: "kept", text: t("pages.policy.content.theReportsYouSubmit") },
    ],
  },
  {
    title: t("pages.policy.content.whatWeDoNotStore"),
    items: [
      { mark: "never", text: t("pages.policy.content.emailAddressPhoneNumberIdDocumentOr") },
      { mark: "never", text: t("pages.policy.content.yourPasswordOnlyAnUnreadableHashIs") },
      { mark: "never", text: t("pages.policy.content.requestsMadeWithoutAnAccountDataIs") },
      { mark: "never", text: t("pages.policy.content.whoMadeEachCalculationRequestOnlyTotals") },
    ],
  },
  {
    title: t("pages.policy.content.whatWeUseItFor"),
    items: [
      { mark: "note", text: t("pages.policy.content.toDisplayYourFarmAndUseYour") },
      {
        mark: "note",
        text: t("pages.policy.content.yourPlantingsContributeAnonymouslyToMunicipalityTotals"),
      },
      { mark: "note", text: t("pages.policy.content.itIsNotUsedForAnyOther") },
    ],
  },
  {
    title: t("pages.policy.content.whoCanSeeIt"),
    items: [
      { mark: "note", text: t("pages.policy.content.youUsingYourUsernameAndPassword") },
      { mark: "note", text: t("pages.policy.content.itIsStoredInACloudDatabase") },
      {
        mark: "note",
        text: t("pages.policy.content.supportCanViewYourPlotsToHelp"),
      },
    ],
  },
  {
    title: t("pages.policy.content.howToWriteToUs"),
    items: [
      { mark: "note", text: t("pages.policy.content.toAskWriteFromMyAccount") },
      { mark: "note", text: t("pages.policy.content.weAnswerWithinDeadlines") },
      { mark: "note", text: t("pages.policy.content.noAccountNothingKept") },
      { mark: "note", text: t("pages.policy.content.controllerAndPendingEmail") },
    ],
  },
  {
    title: t("pages.policy.content.howLongItIsKeptAndHow"),
    items: [
      { mark: "note", text: t("pages.policy.content.dataIsKeptWhileYouHaveAn") },
      { mark: "note", text: t("pages.policy.content.inMyAccountYouCanViewWhat") },
      {
        mark: "note",
        text: t("pages.policy.content.deletingTheAccountDeletesEverythingUsernameSessions"),
      },
    ],
  },
  {
    title: t("pages.policy.content.inYourBrowser"),
    items: [
      { mark: "note", text: t("pages.policy.content.oneCookieForYourSessionNoAdvertising") },
      {
        mark: "note",
        text: t("pages.policy.content.lightModeSoundAndWithoutAnAccount"),
      },
    ],
  },
];
