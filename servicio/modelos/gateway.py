from servicio.datos.ollama import ModelUnavailable


class ModelGateway:
    def __init__(self,adapter,simple_model,complex_model):
        self.adapter=adapter
        self.simple=simple_model
        self.complex=complex_model

    def route(self,function_name):
        # Política inicial explícita; debe contrastarse con casos de prueba.
        if function_name=='mapa-evidencia':
            return self.complex,'analisis_complejo'
        return self.simple,'exploracion'

    def invoke(self,function_name,messages,preferred_model=None,allow_fallback=True):
        return self._invoke(function_name,messages,preferred_model,allow_fallback,
                            json_mode=function_name=='mapa-evidencia')

    def invoke_structured(self,function_name,messages,preferred_model=None,
                          allow_fallback=True):
        """Exige JSON en Ollama para comparaciones científicas estructuradas."""
        return self._invoke(function_name,messages,preferred_model,allow_fallback,
                            json_mode=True)

    def _invoke(self,function_name,messages,preferred_model,allow_fallback,json_mode):
        primary,route=self.route(function_name)
        if preferred_model:
            primary=preferred_model
            route='seleccion_manual'
        backup=self.simple if primary==self.complex else self.complex
        try:
            return self.adapter.chat(messages,primary,json_mode=json_mode),primary,route
        except ModelUnavailable:
            # Una comparación debe ejecutar exactamente el modelo indicado.
            # Sustituirlo silenciosamente sesgaría los resultados.
            if not allow_fallback or preferred_model or primary==backup:
                raise
            return self.adapter.chat(messages,backup,json_mode=json_mode),backup,route+'_respaldo'

