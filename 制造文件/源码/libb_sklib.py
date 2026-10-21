from collections import defaultdict
from skidl import Pin, Part, Alias, SchLib, SKIDL, TEMPLATE

from skidl.pin import pin_types

SKIDL_lib_version = '0.0.1'

libb = SchLib(tool=SKIDL).add_parts(*[
        Part(**{ 'name':'Conn_01x05', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Conn_01x05'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_JST:JST_PH_S5B-PH-SM4-TB_1x05-1MP_P2.00mm_Horizontal', 'keywords':'connector', 'description':'Generic connector, single row, 01x05, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='Pin_3',func=pin_types.PASSIVE,unit=1),
            Pin(num='4',name='Pin_4',func=pin_types.PASSIVE,unit=1),
            Pin(num='5',name='Pin_5',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'D_TVS', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'D_TVS'}), 'ref_prefix':'D', 'fplist':[''], 'footprint':'Diode_SMD:D_SOD-123F', 'keywords':'diode TVS thyrector', 'description':'Bidirectional transient-voltage-suppression diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='A1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C'}), 'ref_prefix':'C', 'fplist':[''], 'footprint':'Capacitor_SMD:C_0805_2012Metric', 'keywords':'cap capacitor', 'description':'Unpolarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'LM66100', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'LM66100'}), 'ref_prefix':'U', 'fplist':['Package_TO_SOT_SMD:SOT-363_SC-70-6'], 'footprint':'Package_TO_SOT_SMD:SOT-363_SC-70-6', 'keywords':'', 'description':'5.5V 1.5A ideal diode, TI, LCSC C2869734', 'datasheet':'', 'pins':[
            Pin(num='1',name='VIN',func=pin_types.PWRIN,unit=1),
            Pin(num='2',name='GND',func=pin_types.PWRIN,unit=1),
            Pin(num='3',name='~{CE}',func=pin_types.INPUT,unit=1),
            Pin(num='4',name='NC',func=pin_types.NOCONNECT,unit=1),
            Pin(num='5',name='~{ST}',func=pin_types.OPENCOLL,unit=1),
            Pin(num='6',name='VOUT',func=pin_types.PWROUT,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'R', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R'}), 'ref_prefix':'R', 'fplist':[''], 'footprint':'Resistor_SMD:R_0603_1608Metric', 'keywords':'R res resistor', 'description':'Resistor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'AO3401A', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'AO3401A'}), 'ref_prefix':'Q', 'fplist':['Package_TO_SOT_SMD:SOT-23', 'Package_TO_SOT_SMD:SOT-23'], 'footprint':'Package_TO_SOT_SMD:SOT-23', 'keywords':'P-Channel MOSFET', 'description':'-4.0A Id, -30V Vds, P-Channel MOSFET, SOT-23', 'datasheet':'http://www.aosmd.com/pdfs/datasheet/AO3401A.pdf', 'pins':[
            Pin(num='1',name='G',func=pin_types.INPUT,unit=1),
            Pin(num='2',name='S',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='D',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'D_Schottky', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'D_Schottky'}), 'ref_prefix':'D', 'fplist':[''], 'footprint':'Diode_SMD:D_SOD-123', 'keywords':'diode Schottky', 'description':'Schottky diode', 'datasheet':'', 'pins':[
            Pin(num='1',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='A',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'C_Polarized', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'C_Polarized'}), 'ref_prefix':'C', 'fplist':[''], 'footprint':'hw:SuperCap_D10_L25_Flat_P5.00mm', 'keywords':'cap capacitor', 'description':'Polarized capacitor', 'datasheet':'', 'pins':[
            Pin(num='1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'Conn_01x02', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'Conn_01x02'}), 'ref_prefix':'J', 'fplist':[''], 'footprint':'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal', 'keywords':'connector', 'description':'Generic connector, single row, 01x02, script generated (kicad-library-utils/schlib/autogen/connector/)', 'datasheet':'', 'pins':[
            Pin(num='1',name='Pin_1',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='Pin_2',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'BAT54S', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'BAT54S'}), 'ref_prefix':'D', 'fplist':['Package_TO_SOT_SMD:SOT-23'], 'footprint':'Package_TO_SOT_SMD:SOT-23', 'keywords':'schottky diode', 'description':'Vr 30V, If 200mA, Dual schottky barrier diode, in series, SOT-323', 'datasheet':'https://www.diodes.com/assets/Datasheets/ds11005.pdf', 'pins':[
            Pin(num='1',name='A',func=pin_types.PASSIVE,unit=1),
            Pin(num='2',name='K',func=pin_types.PASSIVE,unit=1),
            Pin(num='3',name='COM',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'TestPoint', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'TestPoint'}), 'ref_prefix':'TP', 'fplist':[''], 'footprint':'TestPoint:TestPoint_Pad_D1.5mm', 'keywords':'test point tp', 'description':'test point', 'datasheet':'', 'pins':[
            Pin(num='1',name='1',func=pin_types.PASSIVE,unit=1)], 'unit_defs':[] }),
        Part(**{ 'name':'MountingHole', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'MountingHole'}), 'ref_prefix':'H', 'fplist':[''], 'footprint':'MountingHole:MountingHole_2.2mm_M2', 'keywords':'mounting hole', 'description':'Mounting Hole without connection', 'datasheet':'' })])