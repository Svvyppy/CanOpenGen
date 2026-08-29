# PDO Mapping

Phase 4 resolves symbolic TPDO and RPDO entries to deterministic qualified object or
record-field identities. The owning Device/Module namespace wins for local keys;
unqualified imported keys must be unique; explicit names such as
`Diagnostics.supply_voltage` select one module target.

The dedicated PDO phase will validate access/direction and datatype mappability,
calculate numeric mapping entries, and reject classic CANopen payloads above 64 bits.
Advanced communication parameters are outside the MVP scope.
