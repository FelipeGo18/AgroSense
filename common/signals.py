"""Las seis señales del P0, en el orden del contrato (specs/01-reglas.md). Constante pura: no lee archivos, para que
el motor (desempates, HU-192) y la configuración (pesos, HU-075; fuentes, HU-122) la compartan sin que nadie
dependa de nadie (R6)."""

P0_SIGNALS = ("water", "frost", "heat", "soil", "supply", "market")
