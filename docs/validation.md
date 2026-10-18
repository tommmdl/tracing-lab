# O que foi colocado à prova

[English](validation.en.md) · [Voltar](../README.md)

As 19 verificações locais passaram. O [registro completo](../evidence/local-results.json) guarda horário UTC, versões, imagem e o trace ID. O [resumo dos spans](../evidence/trace-summary.json) mostra a relação entre o span HTTP e o span do cliente de banco, sem publicar todo o conteúdo de atributos.

O teste enviou um traceparent conhecido para GET /notes. O ID voltou na resposta; o Tempo recebeu o trace real pelo SDK e Collector. O pai recebido foi preservado no span Flask e o span PostgreSQL ficou como filho dele. O trace incluiu uma operação SELECT.

Um POST criou uma nota temporária e o DELETE removeu somente essa nota. O título não apareceu no trace consultado. Uma rota inexistente manteve a resposta 404, registrada no atributo HTTP. O teste também buscou o trace pelo Grafana e o mesmo ID em logs coletados pelo Alloy e armazenados no Loki. Prometheus e Loki continuaram saudáveis como datasources.

A pipeline cria um cluster novo, instala os projetos Kubernetes, monitoramento e logging em revisões fixas, constrói a mesma variante de instrumentação, sobe Tempo e Collector e repete o teste. No CI, o patch é aplicado sem Argo CD, em um cluster descartável. Localmente, o Argo CD aplica a opção `workloads/notes-traced` pelo Git e mantém self-heal ligado.

Não foram testados retenção por 24 horas, perda de nó, recuperação de backup, fila durável do Collector, métricas geradas por spans ou carga. O teste não comprova mascaramento geral de dados, persistência de traces após substituir o Pod do Tempo nem entrega sem perdas em interrupções. Tempo usa um volume local e uma réplica.

O resultado do GitHub Actions será registrado depois da primeira execução.
