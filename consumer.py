from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, col, sum, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, ArrayType

kafka_bootstrap_servers = "localhost:9092"
kafka_topic = "vendas-ecommerce"

if __name__ == "__main__":
    spark = SparkSession.builder.appName("EcommerceConsumer").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    vendas_schema = StructType([
        StructField("id_ordem", StringType(), True),
        StructField("documento_cliente", StringType(), True),
        StructField("produtos_comprados", ArrayType(StructType([
            StructField("nome", StringType(), True),
            StructField("quantidade", IntegerType(), True),
            StructField("preco_unitario", FloatType(), True)
        ])), True),
        StructField("valor_total_venda", FloatType(), True),
        StructField("data_hora_venda", StringType(), True)
    ])

    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "latest") \
        .load()

    df_string = df.selectExpr("CAST(value AS STRING)")

    df_parsed = df_string.select(from_json(col("value"), vendas_schema).alias("data")).select("data.*")

    df_exploded = df_parsed.withColumn("produto", explode(col("produtos_comprados")))

    df_aggregated = df_exploded \
        .groupBy("produto.nome") \
        .agg(sum(col("produto.quantidade") * col("produto.preco_unitario")).alias("valor_total")) \
        .orderBy("produto.nome")

    query = df_aggregated \
        .writeStream \
        .outputMode("complete") \
        .format("console") \
        .start()

    query.awaitTermination()

    spark.stop()