configuracion = {
    "NOVEDADES":{
        "usecols":["VNTCEDULA","NOTA","VNTNEWFEC","VNTNEWUSER","VNTTIPO",
                   "VTTNOMBRE","VALOR","ALARMA", "TELF","MOVIL"],
        "rename_map":{
                      "VNTCEDULA":"Cedula_Cliente",
                      "VNTTIPO":"Codigo_Novedad",
                      "VTTNOMBRE":"Tipo_Novedad",
                      "ALARMA":"Fecha_Compromiso",
                      "VNTNEWFEC":"Fecha_Novedad",
                      "VNTNEWUSER":"Usuario_Novedad",
                      "NOTA":"Novedad",
                      "VALOR":"Valor",
                      "TELF":"Telefono_Cliente",
                      "MOVIL":"Celular_Cliente"
                      }
    },
    "ANALISIS":{
        "engine": "xlrd",
        "usecols":["diasatras","tipo","numero","ultpago"],
        "rename_map":{
                      "tipo":"Tipo_Credito", 
                      "numero":"Numero_Credito",
                      "diasatras":"Dias_Atraso_Final",
                      "ultpago":"Fecha_Ultimo_pago"
        }
    },
    "R91": {
        "usecols": ["COBRO_DC_A","COBRO_DC_2","COBRO_ATRA","COBRO_ANTI","MCDTIPCRU1","MCDNUMCRU1"],
        "rename_map": { 
                       "MCDNUMCRU1": "Numero_Credito",
                       "MCDTIPCRU1": "Tipo_Credito", 
                       "COBRO_DC_A": "Recaudo_DC_Al_Dia",
                       "COBRO_DC_2": "Recaudo_DC_Atraso",
                       "COBRO_ATRA": "Recaudo_Atraso",
                       "COBRO_ANTI":"Recaudo_Anticipado"
                        }
    },
    "USUARIOS": {
        "usecols": ["CEDULA","NOMBRE","USUARIO","AGRUPACIÓN","NUMERO CORPORATIVO"],
        "rename_map": { 
                       "AGRUPACIÓN": "Cargo_Usuario",
                       "NOMBRE": "Nombre_Usuario",
                       "CEDULA":"Cedula_Usuario", 
                       "USUARIO": "Usuario_Novedad",
                       "NUMERO CORPORATIVO": "Celular_Corporativo"
                        }
    },
    "CALL_CENTER": {
        "sheets": [{ 
              "sheet_name": "Llamadas_Call", 
              "usecols":["Fecha","Fuente", "Destino", "Estado", "Duración", "Recording","UniqueID"], 
              "rename_map": { 
                              "Fecha":"Fecha_Llamada",
                              "Destino": "Destino_Llamada", 
                              "Estado": "Estado_Llamada", 
                              "Duración": "Duracion_Llamada",
                              "Fuente":"Extension_Llamada",
                              "Recording":"Grabacion_Llamada",
                              "UniqueID":"Codigo_Llamada"}, 
              },
            { 
              "sheet_name": "Flujos",
              "usecols": ["CC", "Encargado","Extension Llamada", "Flujo Truora"], 
              "rename_map": { 
                              "CC": "Call_Center",
                              "Encargado": "Nombre_Call",
                              "Extension Llamada": "Extension_Llamada",
                              "Flujo Truora":"Flujo_Truora"},
              },
            { 
              "sheet_name": "Mensajeria_Call",
              "usecols": ["Pais", "Numero de telefono", "Estado de respuesta del outbound","Estado", "Mensaje de inicio",
                          "ID del flujo","Nombre del outbound","Estado del outbound","Primer Mensaje de Agente de Conversacion","Fecha de creacion",
                          "Labels de Conversacion",], 
              "rename_map": { 
                              "Pais": "Codigo_Pais",
                              "Numero de telefono": "Numero_Telefono",
                              "Estado de respuesta del outbound":"Estado_Respuesta_Saliente",
                              "Estado":"Estado",
                              "Estado del outbound":"Estado_Mensaje",
                              "Mensaje de inicio":"Respuesta_Saliente",
                              "Nombre del outbound":"Nombre_Saliente",
                              "Primer Mensaje de Agente de Conversacion":"Primer_Mensaje_Agente",
                              "Fecha de creacion":"Fecha_Llamada",
                              "ID del flujo":"Flujo_Truora",
                              "Labels de Conversacion":"Etiquetas_Conversacion"}
              }
        ]   
    },
    #Tipos de datos para reporte base
    "BASE_MENSUAL": {
        "dtype_map": {
            'Empresa':str,
            'Cedula_Cliente': str,
            'Numero_Credito': str,
            'Primera_Cuota_Mora':str,
            'Cantidad_Producto':int,                    
            'Cantidad_Obsequio':int,
            'Valor_Cuota': float,        
            'Saldo_Capital': float,
            'Valor_Desembolso': float,               
            'Meta_Intereses':float,          
            'Meta_General':float,
            'Meta_Saldo':float,
            'Meta_$':float,
            'Meta_T.R_$':float,
            'Valor_Cuota_Atraso':str,
            'Valor_Vencido':float,
            'Valor_Cuota_Vigente':str,
            'Total_Cuotas': 'Int64',
            'Cuotas_Pagadas':'Int64',                    
            'Dias_Atraso':'Int64',
        }
    }
}