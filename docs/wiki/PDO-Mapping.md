# PDO Mapping

CanOpenGen resolves symbolic TPDO and RPDO entries to deterministic qualified object or
record-field identities. The owning Device/Module namespace wins for local keys;
unqualified imported keys must be unique; explicit names such as
`Diagnostics.supply_voltage` select one module target.

The PDO backend validates access direction and datatype mappability, calculates numeric
mapping entries, and rejects classic CANopen payloads above 64 bits. Advanced
communication parameters are outside the MVP scope.
