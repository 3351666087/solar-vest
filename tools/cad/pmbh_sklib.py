from collections import defaultdict
from skidl import Pin, Part, Alias, SchLib, SKIDL, TEMPLATE

from skidl.pin import pin_types

SKIDL_lib_version = '0.0.1'

pmbh = SchLib(tool=SKIDL).add_parts(*[
        Part(**{ 'name':'Screw_Terminal_01x02', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Screw_Terminal_01x02'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal', 'keywords':'screw terminal', 'description':'Generic screw terminal, single row, 01x02, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'Polyfuse', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Polyfuse'}), 'ref_prefix':'F', 'fplist':[''], 'footprint':'Fuse:Fuse_1812_4532Metric', 'keywords':'resettable fuse PTC PPTC polyfuse polyswitch', 'description':'Resettable fuse, polymeric positive temperature coefficient', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'AO3401A', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'AO3401A'}), 'ref_prefix':'Q', 'fplist':['Package_TO_SOT_SMD:SOT-23', 'Package_TO_SOT_SMD:SOT-23'], 'footprint':'Package_TO_SOT_SMD:SOT-23', 'keywords':'P-Channel MOSFET', 'description':'-4.0A Id, -30V Vds, P-Channel MOSFET, SOT-23', 'datasheet':'http://www.aosmd.com/pdfs/datasheet/AO3401A.pdf', 'pins':[
            Pin(num='1',name='G',func=pin_types.INPUT,unit=1),
            Pin(num='2',name='S',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='D',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'R', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R'}), 'ref_prefix':'R', 'fplist':[''], 'footprint':'Resistor_SMD:R_0603_1608Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'AO3400A', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'AO3400A'}), 'ref_prefix':'Q', 'fplist':['', 'Package_TO_SOT_SMD:SOT-23'], 'footprint':'Package_TO_SOT_SMD:SOT-23', 'keywords':'N-Channel MOSFET', 'description':'30V Vds, 5.7A Id, N-Channel MOSFET, SOT-23', 'datasheet':'http://www.aosmd.com/pdfs/datasheet/AO3400A.pdf', 'pins':[
            Pin(num='1',name='G',func=pin_types.INPUT,unit=1),
            Pin(num='2',name='S',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='D',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'D_Zener', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'D_Zener'}), 'ref_prefix':'D', 'fplist':[''], 'footprint':'Diode_SMD:D_SOD-123', 'keywords':'diode', 'description':'Zener diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'SMAJ10A', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'SMAJ10A'}), 'ref_prefix':'D', 'fplist':['Diode_SMD:D_SMB', 'Diode_SMD:D_SMA'], 'footprint':'Diode_SMD:D_SMA', 'keywords':'unidirectional diode TVS voltage suppressor', 'description':'400W unidirectional Transient Voltage Suppressor, 10.0Vr, SMA(DO-214AC)', 'datasheet':'https://www.littelfuse.com/media?resourcetype=datasheets&itemid=75e32973-b177-4ee3-a0ff-cedaf1abdb93&filename=smaj-datasheet', 'pins':[
            Pin(num='1',name='A1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C'}), 'ref_prefix':'C', 'fplist':[''], 'footprint':'Capacitor_SMD:C_0805_2012Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_Polarized', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_Polarized'}), 'ref_prefix':'C', 'fplist':[''], 'footprint':'Capacitor_SMD:CP_Elec_6.3x7.7', 'keywords':'cap capacitor', 'description':'Polarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'NetTie_2', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'NetTie_2'}), 'ref_prefix':'NT', 'fplist':[''], 'footprint':'NetTie:NetTie-2_SMD_Pad0.5mm', 'keywords':'net tie short', 'description':'Net tie, 2 pins', 'datasheet':'', 'pins':[
            Pin(num='1',name='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'D_Schottky', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'D_Schottky'}), 'ref_prefix':'D', 'fplist':[''], 'footprint':'Diode_SMD:D_SOD-123', 'keywords':'diode Schottky', 'description':'Schottky diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'CN3791', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'CN3791'}), 'ref_prefix':'U', 'fplist':['Package_SO:SSOP-10_3.9x4.9mm_P1.00mm'], 'footprint':'Package_SO:SSOP-10_3.9x4.9mm_P1.00mm', 'keywords':'', 'description':'4A Li-ion charger with photovoltaic MPPT, Consonance, LCSC C154992', 'datasheet':'', 'pins':[
            Pin(num='1',name='VG',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='3',name='~{CHRG}',func=pin_types.OPENCOLL,unit=1),
            Pin(num='4',name='~{DONE}',func=pin_types.OPENCOLL,unit=1),
            Pin(num='5',name='COM',func=pin_types.PASSIVE,unit=1),
            Pin(num='6',name='MPPT',func=pin_types.INPUT,unit=1),
            Pin(num='7',name='BAT',func=pin_types.INPUT,unit=1),
            Pin(num='8',name='CSP',func=pin_types.INPUT,unit=1),
            Pin(num='9',name='VCC',func=pin_types.PWRIN,unit=1),
            Pin(num='10',name='DRV',func=pin_types.OUTPUT,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'SS34', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'SS34'}), 'ref_prefix':'D', 'fplist':['Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal', 'Diode_SMD:D_SMA'], 'footprint':'Diode_SMD:D_SMA', 'keywords':'diode Schottky', 'description':'40V 3A Schottky Diode, SMA', 'datasheet':'https://www.vishay.com/docs/88751/ss32.pdf', 'pins':[
            Pin(num='1',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'L', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'L'}), 'ref_prefix':'L', 'fplist':[''], 'footprint':'Inductor_SMD:L_Sunlord_SWPA6045S', 'keywords':'inductor choke coil reactor magnetic', 'description':'Inductor', 'datasheet':'', 'pins':[
            Pin(num='1',name='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'Conn_01x02', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Conn_01x02'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal', 'keywords':'connector', 'description':'Generic connector, single row, 01x02, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'D_TVS', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'D_TVS'}), 'ref_prefix':'D', 'fplist':[''], 'footprint':'Diode_SMD:D_SOD-123F', 'keywords':'diode TVS thyrector', 'description':'Bidirectional transient-voltage-suppression diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='A1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'Conn_01x05', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Conn_01x05'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_JST:JST_PH_S5B-PH-SM4-TB_1x05-1MP_P2.00mm_Horizontal', 'keywords':'connector', 'description':'Generic connector, single row, 01x05, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='Pin_3',func=pin_types.PASSIVE,unit=1),
            Pin(num='4',name='Pin_4',func=pin_types.PASSIVE,unit=1),
            Pin(num='5',name='Pin_5',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'ME6211C33M5', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'ME6211C33M5'}), 'ref_prefix':'U', 'fplist':['Package_TO_SOT_SMD:SOT-23-5'], 'footprint':'Package_TO_SOT_SMD:SOT-23-5', 'keywords':'linear regulator ldo fixed positive', 'description':'500mA low dropout linear regulator, shutdown pin, 6.5V max input voltage, 3.3V fixed positive output, SOT-23-5', 'datasheet':'https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_MICRONE-Nanjing-Micro-One-Elec-ME6211C33R5G_C235316.pdf', 'pins':[
            Pin(num='1',name='V_{IN}',func=pin_types.PWRIN,unit=1),
            Pin(num='2',name='V_{SS}',func=pin_types.PWRIN,unit=1),
            Pin(num='3',name='CE',func=pin_types.INPUT,unit=1),
            Pin(num='4',name='NC',func=pin_types.NOCONNECT,unit=1),
            Pin(num='5',name='V_{OUT}',func=pin_types.PWROUT,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'INA226', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'INA226'}), 'ref_prefix':'U', 'fplist':['Package_SO:TSSOP-10_3x3mm_P0.5mm'], 'footprint':'Package_SO:MSOP-10_3x3mm_P0.5mm', 'keywords':'ADC I2C 16-Bit Oversampling Current Shunt', 'description':'High-Side or Low-Side Measurement, Bi-Directional Current and Power Monitor (0-36V) with I2C Compatible Interface, TSSOP-10 (Texas DGS0010A / VSSOP)', 'datasheet':'http://www.ti.com/lit/ds/symlink/ina226.pdf', 'pins':[
            Pin(num='1',name='A1',func=pin_types.INPUT,unit=1),
            Pin(num='2',name='A0',func=pin_types.INPUT,unit=1),
            Pin(num='3',name='~{Alert}',func=pin_types.OPENCOLL,unit=1),
            Pin(num='4',name='SDA',func=pin_types.BIDIR,unit=1),
            Pin(num='5',name='SCL',func=pin_types.INPUT,unit=1),
            Pin(num='6',name='VS',func=pin_types.PWRIN,unit=1),
            Pin(num='7',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='8',name='Vbus',func=pin_types.INPUT,unit=1),
            Pin(num='9',name='Vin-',func=pin_types.INPUT,unit=1),
            Pin(num='10',name='Vin+',func=pin_types.INPUT,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'Conn_01x07', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Conn_01x07'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical', 'keywords':'connector', 'description':'Generic connector, single row, 01x07, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='Pin_3',func=pin_types.PASSIVE,unit=1),
            Pin(num='4',name='Pin_4',func=pin_types.PASSIVE,unit=1),
            Pin(num='5',name='Pin_5',func=pin_types.PASSIVE,unit=1),
            Pin(num='6',name='Pin_6',func=pin_types.PASSIVE,unit=1),
            Pin(num='7',name='Pin_7',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'XIAO_nRF52840_Sense', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'XIAO_nRF52840_Sense'}), 'ref_prefix':'M', 'fplist':[''], 'footprint':'', 'keywords':'', 'description':'Seeed XIAO nRF52840 Sense (pre-soldered), plugs into J4/J5 sockets; not placed on the PCB', 'datasheet':'', 'pins':[
            Pin(num='1',name='D0/A0',func=pin_types.BIDIR,unit=1),
            Pin(num='2',name='D1/A1',func=pin_types.BIDIR,unit=1),
            Pin(num='3',name='D2/A2',func=pin_types.BIDIR,unit=1),
            Pin(num='4',name='D3/A3',func=pin_types.BIDIR,unit=1),
            Pin(num='5',name='D4/SDA',func=pin_types.BIDIR,unit=1),
            Pin(num='6',name='D5/SCL',func=pin_types.BIDIR,unit=1),
            Pin(num='7',name='D6/TX',func=pin_types.BIDIR,unit=1),
            Pin(num='8',name='D7/RX',func=pin_types.BIDIR,unit=1),
            Pin(num='9',name='D8/SCK',func=pin_types.BIDIR,unit=1),
            Pin(num='10',name='D9/MISO',func=pin_types.BIDIR,unit=1),
            Pin(num='11',name='D10/MOSI',func=pin_types.BIDIR,unit=1),
            Pin(num='12',name='3V3',func=pin_types.PWRIN,unit=1),
            Pin(num='13',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='14',name='5V',func=pin_types.PWRIN,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'TestPoint', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'TestPoint'}), 'ref_prefix':'TP', 'fplist':[''], 'footprint':'TestPoint:TestPoint_Pad_D1.5mm', 'keywords':'test point tp', 'description':'test point', 'datasheet':'', 'pins':[
            Pin(num='1',name='1',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'MountingHole', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'MountingHole'}), 'ref_prefix':'H', 'fplist':[''], 'footprint':'MountingHole:MountingHole_2.2mm_M2', 'keywords':'mounting hole', 'description':'Mounting Hole without connection', 'datasheet':'' })])