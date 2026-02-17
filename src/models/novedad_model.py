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
              "usecols": ["SOURCE_FILE", "Phone Number", "Outbound Name","Status","Message Status","Process Status",
                          "Outbound Response Status","Flow ID","Outbound Name","Process Failure",
                          "Agent Conversation First Response Message Type",], 
              "rename_map": { 
                              "SOURCE_FILE":"Fecha_Mensaje",
                              "Phone Number": "Numero_Telefono",
                              "Estado de respuesta del outbound":"Estado_Respuesta_Saliente",
                              "Outbound Name":"Nombre_Saliente",
                              "Status":"Estado",
                              "Message Status":"Estado_Mensaje",
                              "Process Status":"Estado_Proceso",
                              "Outbound Response Status":"Estado_Respuesta_Entrante",
                              "Flow ID":"Flujo_Truora",
                              "Outbound Name":"Nombre_Saliente",
                              "Process Failure":"Fallo_Proceso",
                              "Agent Conversation First Response Message Type":"Tipo_Respuesta_Agente",
                              }
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