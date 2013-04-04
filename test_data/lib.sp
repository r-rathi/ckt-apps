$.macromodel c c
$+ c=1e-15

.macromodel pch pmos d g s b m=1
+ cg="0.05 * w * l * m"

.macromodel nch nmos d g s b m=1
+ cg="0.05 * w * l * m"

.macromodel pch_mac pmos d g s b m=1
+ cg="0.05 * w * l * m"

.macromodel nch_mac nmos d g s b m=1
+ cg="0.05 * w * l * m"
