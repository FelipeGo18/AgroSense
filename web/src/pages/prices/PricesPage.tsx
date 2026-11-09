import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError } from "@/api/client";
import { Footer } from "@/components/layout/Footer";
import { TopBar } from "@/components/layout/TopBar";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChoiceGroup } from "@/components/ui/ChoiceGroup";
import { TextField } from "@/components/ui/TextField";
import {
  changeText,
  formatDay,
  formatPesos,
  formatUpdated,
  monthName,
  searchKey,
  seasonExtremes,
  seasonPercent,
  useMarketPrices,
  useProductHistory,
  type Price,
  type ProductPrice,
} from "@/features/market/prices";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { PriceChart, SeasonChart } from "./charts";

/** «Corabastos (Bogotá)» → «Corabastos»: el nombre corto va en el botón y el completo, debajo. */
const shortName = (name: string) => name.split(" (")[0];

const NOT_FORECAST = "Así se ha movido el precio en la central. No es un pronóstico.";
/**
 * La cita textual que piden los términos del DANE (HU-221) llega de la API tal cual, de la fila de su fuente; después,
 * qué datos son. Una fuente sin cita no la tiene: no se inventa.
 */
const sourceText = (citation: string | null) => `${citation ? `${citation}. ` : ""}Datos de SIPSA, precios mayoristas diarios.`;

/**
 * Precios en la central de abastos (HU-221): el último precio por kilo de cada producto en Corabastos o en Tunja, según
 * SIPSA del DANE, y, al abrir uno, su último año y en qué meses suele estar más caro o más barato. Se puede ver sin
 * cuenta. La central y el producto van en la dirección (`?central=1&producto=papa-negra`): se pueden compartir.
 * Es una página quieta: no tiene nada que animar, así que se ve igual en modo ligero.
 */
export function PricesPage() {
  const [params, setParams] = useSearchParams();
  const marketId = params.get("central");
  const productId = params.get("producto");
  const prices = useMarketPrices(marketId);
  const [query, setQuery] = useState("");

  const choose = (next: { central?: string | null; producto?: string | null }) => {
    const merged = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) merged.set(key, value);
      else merged.delete(key);
    }
    setParams(merged, { preventScrollReset: true });
  };

  return (
    <div className="min-h-svh bg-paleta-niebla">
      <title>Precios en la central de abastos · AgroSense</title>
      <TopBar />
      {/* El espacio de abajo es para los cerros del pie de página. */}
      <main className="container-page pt-[112px] pb-40 md:pt-[128px] md:pb-48">
        <header className="flex max-w-[880px] min-w-0 flex-col gap-3">
          <Eyebrow>Precios mayoristas</Eyebrow>
          <h1 className="text-[clamp(1.75rem,4vw,3rem)]">¿A cuánto se paga en la central?</h1>
          <p>
            El precio por kilo que el DANE registra cada día en la central de abastos. Es el precio al por mayor, lo que se paga en la
            central, no en la tienda.
          </p>
        </header>

        {prices.isPending ? (
          <p role="status" className="mt-8">
            Cargando los precios…
          </p>
        ) : prices.isError ? (
          <div className="mt-8 flex max-w-[880px] flex-col gap-3">
            <Alert>
              {prices.error instanceof ApiError && prices.error.status === 503
                ? prices.error.message
                : "No pudimos cargar los precios. Intente de nuevo en un momento."}
            </Alert>
            <Button variant="secondary" className="self-start" onClick={() => void prices.refetch()}>
              Volver a intentar
            </Button>
          </div>
        ) : (
          <>
            <div className="mt-6 grid max-w-[880px] grid-cols-1 gap-4 md:grid-cols-2">
              <ChoiceGroup
                legend="Central de abastos"
                choices={prices.data.markets.map((m) => ({ value: m.market_id, label: shortName(m.name) }))}
                value={prices.data.market.market_id}
                onChange={(value) => choose({ central: value, producto: null })}
                hint={prices.data.market.name}
              />
              <TextField
                label="Buscar producto"
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Por ejemplo, papa"
              />
            </div>
            <p className="mt-4 text-[15px] text-texto-secundario">
              Precios del {formatDay(prices.data.date)} en {prices.data.market.name}.
              {prices.data.updated_at &&
                ` Actualizados del DANE el ${formatUpdated(prices.data.updated_at)}; se actualizan de lunes a viernes.`}{" "}
              {sourceText(prices.data.citation)}
            </p>

            <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:items-start">
              {productId && (
                <div className="lg:sticky lg:top-28 lg:order-2">
                  <ProductDetail productId={productId} marketId={marketId} onClose={() => choose({ producto: null })} />
                </div>
              )}
              <ProductList
                products={prices.data.products}
                marketDate={prices.data.date}
                query={query}
                selected={productId}
                link={(id) => {
                  const next = new URLSearchParams(params);
                  next.set("producto", id);
                  return `?${next}`;
                }}
              />
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}

/** Los productos de la central por grupo (tubérculos, verduras, frutas), con el filtro de la búsqueda. */
function ProductList({
  products,
  marketDate,
  query,
  selected,
  link,
}: {
  products: ProductPrice[];
  marketDate: string;
  query: string;
  selected: string | null;
  link: (productId: string) => string;
}) {
  const key = searchKey(query);
  const shown = products.filter((p) => searchKey(p.product).includes(key));
  if (shown.length === 0) {
    return <p className="lg:order-1">No hay precios de «{query.trim()}» en esta central.</p>;
  }
  const groups = [...new Set(shown.map((p) => p.group))];
  return (
    <div className="flex min-w-0 flex-col gap-6 lg:order-1">
      {groups.map((group) => (
        <section key={group} aria-labelledby={`grupo-${searchKey(group).replace(/\W+/g, "-")}`} className="flex flex-col gap-2">
          <h2
            id={`grupo-${searchKey(group).replace(/\W+/g, "-")}`}
            className="text-[14px] font-bold tracking-wide text-texto-secundario uppercase"
          >
            {group}
          </h2>
          <ul className="flex flex-col gap-2">
            {shown
              .filter((p) => p.group === group)
              .map((p) => (
                <li key={p.product_id}>
                  <ProductRow product={p} marketDate={marketDate} selected={p.product_id === selected} to={link(p.product_id)} />
                </li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

/** Flecha con forma propia: el cambio se lee por la forma y por el texto, no solo por el color. */
function ChangeMark({ change }: { change: number }) {
  if (change === 0) {
    return (
      <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4 shrink-0">
        <rect x="2" y="7" width="12" height="2.5" fill="var(--color-texto-secundario)" />
      </svg>
    );
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className="size-4 shrink-0">
      <polygon
        points={change > 0 ? "8,2 15,13 1,13" : "1,3 15,3 8,14"}
        fill={change > 0 ? "var(--color-paleta-calabaza)" : "var(--color-paleta-cielo)"}
        stroke={change > 0 ? "var(--color-oscuro-calabaza)" : "var(--color-oscuro-cielo)"}
        strokeWidth="1.5"
      />
    </svg>
  );
}

function ProductRow({ product, marketDate, selected, to }: { product: ProductPrice; marketDate: string; selected: boolean; to: string }) {
  const { latest } = product;
  // Un producto que hace rato no tiene precio lo dice: el precio de hace meses no es el de hoy.
  const stale = latest.date !== marketDate;
  return (
    <Link
      to={to}
      preventScrollReset
      aria-current={selected ? "true" : undefined}
      className={`flex min-h-11 flex-wrap items-center justify-between gap-x-4 gap-y-1 border-2 px-4 py-3 hover:brightness-[0.98] ${
        selected ? "border-oscuro-oliva bg-oliva-claro" : "border-superficie-borde bg-superficie-panel"
      }`}
    >
      <span className="flex min-w-0 flex-col">
        <span className="text-[18px] font-bold break-words">{product.product}</span>
        {product.several_varieties && <span className="text-[13px] text-texto-secundario">Varias variedades</span>}
      </span>
      <span className="flex flex-col items-end text-right">
        <span className="text-[18px] font-bold">
          {formatPesos(latest.avg_cop_kg)} <span className="text-[14px] font-normal text-texto-secundario">/kg</span>
        </span>
        {stale ? (
          <span className="text-[13px] font-bold text-oscuro-calabaza">Último precio: {formatDay(latest.date)}</span>
        ) : product.change_pct !== null && product.change_pct !== undefined ? (
          <span className="flex items-center gap-1 text-[13px] text-texto-secundario">
            <ChangeMark change={product.change_pct} />
            {changeText(product.change_pct)}
          </span>
        ) : (
          <span className="text-[13px] text-texto-secundario">Sin precio de hace una semana</span>
        )}
      </span>
    </Link>
  );
}

const range = (price: Price) =>
  price.min_cop_kg != null && price.max_cop_kg != null
    ? `Entre ${formatPesos(price.min_cop_kg)} y ${formatPesos(price.max_cop_kg)} por kilo`
    : "El DANE no dio el mínimo o el máximo de ese día";

/** Un producto: su último precio, su último año y en qué meses suele estar más caro o más barato. */
function ProductDetail({ productId, marketId, onClose }: { productId: string; marketId: string | null; onClose: () => void }) {
  const history = useProductHistory(productId, marketId);
  return (
    <Card bodyClassName="gap-4">
      {history.isPending ? (
        <p role="status">Cargando el precio…</p>
      ) : history.isError ? (
        <>
          <Alert>
            {history.error instanceof ApiError && history.error.status === 404
              ? history.error.message
              : "No pudimos cargar este producto. Intente de nuevo en un momento."}
          </Alert>
          <Button variant="secondary" className="self-start" onClick={onClose}>
            Ver todos los productos
          </Button>
        </>
      ) : (
        <>
          <header className="flex flex-col gap-1">
            <h2 className="text-[clamp(1.375rem,2.6vw,1.75rem)]">{history.data.product}</h2>
            <p className="text-[15px] text-texto-secundario">
              {history.data.market.name}
              {history.data.several_varieties ? " · el DANE junta varias variedades" : ""}
            </p>
          </header>
          <div className="flex flex-col">
            <p className="text-[clamp(1.75rem,4vw,2.5rem)] leading-tight font-bold">
              {formatPesos(history.data.latest.avg_cop_kg)} <span className="text-[18px] font-normal">por kilo</span>
            </p>
            <p className="text-[15px] text-texto-secundario">
              Precio medio del {formatDay(history.data.latest.date)}. {range(history.data.latest)}.
            </p>
          </div>

          <section aria-labelledby="ultimo-ano" className="flex flex-col gap-2">
            <h3 id="ultimo-ano" className="text-[20px]">
              El último año
            </h3>
            <PriceChart days={history.data.days} />
          </section>

          <section aria-labelledby="temporada" className="flex flex-col gap-2">
            <h3 id="temporada" className="text-[20px]">
              ¿En qué meses suele estar más caro?
            </h3>
            {history.data.season ? (
              <>
                <SeasonSummary season={history.data.season} />
                <SeasonChart season={history.data.season} />
                <p className="text-[15px] leading-snug text-texto-secundario">
                  Cada barra compara el precio de ese mes con el promedio de su mismo año, en %: así no cuenta la inflación. Con los años
                  completos de {history.data.season.first_year} a {history.data.season.last_year}.
                </p>
              </>
            ) : (
              <p>Todavía no hay suficientes años completos de precios de este producto en esta central para decirlo.</p>
            )}
          </section>

          <p role="note" className="border-l-8 border-paleta-calabaza bg-superficie-panel-suave px-4 py-3 font-bold">
            {NOT_FORECAST}
          </p>
          <p className="text-[14px] text-texto-secundario">{sourceText(history.data.citation)}</p>
          <Button variant="secondary" className="self-start" onClick={onClose}>
            Ver todos los productos
          </Button>
        </>
      )}
    </Card>
  );
}

function SeasonSummary({ season }: { season: NonNullable<Parameters<typeof SeasonChart>[0]["season"]> }) {
  const { cheapest, priciest } = seasonExtremes(season);
  return (
    <p>
      Suele estar más barato en <strong>{monthName(cheapest.month)}</strong> ({seasonPercent(cheapest.seasonal_index)} %) y más caro en{" "}
      <strong>{monthName(priciest.month)}</strong> (+{seasonPercent(priciest.seasonal_index)} %) que el promedio de su año.
    </p>
  );
}
