* Test netlist

********************************************************************************
.subckt inv1 a y vdd vss
mp1 y a vdd vdd pch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9 m=2
mn1 y a vss vss nch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9 m=2

c1 a vss 1e-15
c2 y vss 1.5e-15
c3 y vdd 2.5e-15
.ends

********************************************************************************
.subckt inv2 a y vdd vss wp=200e-9 wn=200e-9
xmp1 y a vdd vdd pch_mac w="wp" l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9
xmn1 y a vss vss nch_mac w="wn" l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9

c1 a vss 1e-15
c2 y vss 1.5e-15
c3 y vdd 2.5e-15
.ends

********************************************************************************
.subckt buf1 a y vdd vss
mp1 n2 a vdd vdd pch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9
mn1 n2 a vss vss nch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9

mp2 y n2 vdd vdd pch w=200e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9
mn2 y n2 vss vss nch w=200e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9

c1  a  vss 1e-15 $ input
c21 n2 vss 1.5e-15
c22 n2 vdd 2.5e-15
c3  y
+ vss 2.0e-15 $ output
.ends

********************************************************************************
.subckt buf2 a y vdd vss
mp1 n2 a vdd vdd pch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9
mn1 n2 a vss vss nch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9

xi2 n2 y vdd vss inv2 $ Note: this refers to the local inv2 below

c1   a vss 1e-15
c21 n2 vss 1.5e-15
c22 n2 vdd 2.5e-15
c3   y vss 2.0e-15

* nested subckt definition inside buf2 (different from global inv2)
.subckt inv2 a y vdd vss
mp1 y a vdd vdd pch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9
mn1 y a vss vss nch w=100e-9 l=20e-9 ad=7e-15 as=7e-15 pd=270e-9 ps=270e-9

c1 a vss 1e-15
c2 y vss 1.5e-15
c3 y vdd 2.5e-15
.ends

.ends

********************************************************************************
.subckt buf3 a y vdd vss
xi1 a n2 vdd vss inv1
xi2 n2 y vdd vss inv2 $wp=200e-9 wn=200e-9

c1   a vss 1e-15
c21 n2 vss 1.5e-15
c22 n2 vdd 2.5e-15
c3   y vss 2.0e-15
.ends

********************************************************************************
.subckt buf a y vdd vss
xb1 a  n1 vdd vss buf1
xb2 n1 n2 vdd vss buf2
xb3 n2 y  vdd vss buf3
.ends
