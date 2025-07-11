-- MySQL dump 10.13  Distrib 8.0.42, for Linux (x86_64)
--
-- Host: localhost    Database: sistema_inventario
-- ------------------------------------------------------
-- Server version	8.0.42-0ubuntu0.24.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `tb_articulo`
--

DROP TABLE IF EXISTS `tb_articulo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_articulo` (
  `i_id` int NOT NULL,
  `a_c_contable` varchar(20) NOT NULL,
  `a_stockMax` int DEFAULT NULL,
  `a_stockMin` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`i_id`),
  CONSTRAINT `tb_articulo_ibfk_1` FOREIGN KEY (`i_id`) REFERENCES `tb_item` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_articulo`
--

LOCK TABLES `tb_articulo` WRITE;
/*!40000 ALTER TABLE `tb_articulo` DISABLE KEYS */;
INSERT INTO `tb_articulo` (`i_id`, `a_c_contable`, `a_stockMax`, `a_stockMin`, `created_at`, `updated_at`) VALUES (1,'17264858987',100,5,'2025-07-07 03:06:34','2025-07-07 03:06:34'),(2,'168951984984',100,5,'2025-07-07 03:06:55','2025-07-07 03:06:55'),(3,'17264858987r',100,1,'2025-07-07 03:07:15','2025-07-07 03:07:15'),(4,'1689519849842',100,5,'2025-07-07 03:19:49','2025-07-07 03:19:49'),(5,'16895198498424',100,5,'2025-07-07 03:22:06','2025-07-07 03:22:06');
/*!40000 ALTER TABLE `tb_articulo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_consumo`
--

DROP TABLE IF EXISTS `tb_consumo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_consumo` (
  `c_numero` int NOT NULL,
  `c_fecha` date NOT NULL,
  `c_hora` time NOT NULL,
  `c_descripcion` varchar(200) NOT NULL,
  `c_cantidad` int NOT NULL,
  `c_valorUnitario` decimal(10,2) NOT NULL,
  `c_valorTotal` decimal(10,2) NOT NULL,
  `c_observaciones` varchar(500) DEFAULT NULL,
  `c_estado` varchar(20) DEFAULT NULL,
  `c_fecha_devolucion` datetime DEFAULT NULL,
  `c_puede_editar` tinyint(1) DEFAULT NULL,
  `pe_id` int NOT NULL,
  `i_id` int NOT NULL,
  `u_id` int NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pe_id` (`pe_id`),
  KEY `i_id` (`i_id`),
  KEY `u_id` (`u_id`),
  CONSTRAINT `tb_consumo_ibfk_1` FOREIGN KEY (`pe_id`) REFERENCES `tb_persona` (`id`),
  CONSTRAINT `tb_consumo_ibfk_2` FOREIGN KEY (`i_id`) REFERENCES `tb_item` (`id`),
  CONSTRAINT `tb_consumo_ibfk_3` FOREIGN KEY (`u_id`) REFERENCES `tb_usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_consumo`
--

LOCK TABLES `tb_consumo` WRITE;
/*!40000 ALTER TABLE `tb_consumo` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_consumo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_entrada`
--

DROP TABLE IF EXISTS `tb_entrada`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_entrada` (
  `e_fecha` date NOT NULL,
  `e_hora` time NOT NULL,
  `e_descripcion` varchar(200) NOT NULL,
  `e_numFactura` varchar(20) NOT NULL,
  `p_id` int NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `p_id` (`p_id`),
  CONSTRAINT `tb_entrada_ibfk_1` FOREIGN KEY (`p_id`) REFERENCES `tb_proveedores` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_entrada`
--

LOCK TABLES `tb_entrada` WRITE;
/*!40000 ALTER TABLE `tb_entrada` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_entrada` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_instrumento`
--

DROP TABLE IF EXISTS `tb_instrumento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_instrumento` (
  `i_id` int NOT NULL,
  `i_marca` varchar(50) NOT NULL,
  `i_modelo` varchar(50) NOT NULL,
  `i_serie` varchar(50) NOT NULL,
  `i_estado` varchar(50) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`i_id`),
  UNIQUE KEY `i_serie` (`i_serie`),
  CONSTRAINT `tb_instrumento_ibfk_1` FOREIGN KEY (`i_id`) REFERENCES `tb_item` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_instrumento`
--

LOCK TABLES `tb_instrumento` WRITE;
/*!40000 ALTER TABLE `tb_instrumento` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_instrumento` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_item`
--

DROP TABLE IF EXISTS `tb_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_item` (
  `i_codigo` varchar(20) NOT NULL,
  `i_nombre` varchar(200) NOT NULL,
  `i_tipo` varchar(20) NOT NULL,
  `i_cantidad` int DEFAULT NULL,
  `i_vUnitario` decimal(10,2) DEFAULT NULL,
  `i_vTotal` decimal(10,2) DEFAULT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `i_codigo` (`i_codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_item`
--

LOCK TABLES `tb_item` WRITE;
/*!40000 ALTER TABLE `tb_item` DISABLE KEYS */;
INSERT INTO `tb_item` (`i_codigo`, `i_nombre`, `i_tipo`, `i_cantidad`, `i_vUnitario`, `i_vTotal`, `id`, `created_at`, `updated_at`) VALUES ('ART001','Lapiz','articulo',0,0.15,0.00,1,'2025-07-07 03:06:34','2025-07-07 03:06:34'),('ART002','esfero','articulo',0,0.01,0.00,2,'2025-07-07 03:06:55','2025-07-07 03:06:55'),('ART003','guitarra','articulo',0,0.70,0.00,3,'2025-07-07 03:07:15','2025-07-07 03:07:15'),('ART004','musetas','articulo',5,1.00,5.00,4,'2025-07-07 03:19:49','2025-07-07 03:20:00'),('ART005','flauta','articulo',13,2.50,32.50,5,'2025-07-07 03:22:06','2025-07-07 03:22:36');
/*!40000 ALTER TABLE `tb_item` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_movimiento_detalle`
--

DROP TABLE IF EXISTS `tb_movimiento_detalle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_movimiento_detalle` (
  `m_fecha` datetime NOT NULL,
  `m_tipo` varchar(20) NOT NULL,
  `m_cantidad` int NOT NULL,
  `m_valorUnitario` decimal(10,2) NOT NULL,
  `m_valorTotal` decimal(10,2) NOT NULL,
  `m_observaciones` varchar(200) DEFAULT NULL,
  `m_stock_anterior` int DEFAULT NULL,
  `m_stock_actual` int DEFAULT NULL,
  `m_valor_anterior` decimal(10,2) DEFAULT NULL,
  `m_valor_actual` decimal(10,2) DEFAULT NULL,
  `i_id` int NOT NULL,
  `e_id` int DEFAULT NULL,
  `c_id` int DEFAULT NULL,
  `u_id` int NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `i_id` (`i_id`),
  KEY `e_id` (`e_id`),
  KEY `c_id` (`c_id`),
  KEY `u_id` (`u_id`),
  CONSTRAINT `tb_movimiento_detalle_ibfk_1` FOREIGN KEY (`i_id`) REFERENCES `tb_item` (`id`),
  CONSTRAINT `tb_movimiento_detalle_ibfk_2` FOREIGN KEY (`e_id`) REFERENCES `tb_entrada` (`id`),
  CONSTRAINT `tb_movimiento_detalle_ibfk_3` FOREIGN KEY (`c_id`) REFERENCES `tb_consumo` (`id`),
  CONSTRAINT `tb_movimiento_detalle_ibfk_4` FOREIGN KEY (`u_id`) REFERENCES `tb_usuario` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_movimiento_detalle`
--

LOCK TABLES `tb_movimiento_detalle` WRITE;
/*!40000 ALTER TABLE `tb_movimiento_detalle` DISABLE KEYS */;
INSERT INTO `tb_movimiento_detalle` (`m_fecha`, `m_tipo`, `m_cantidad`, `m_valorUnitario`, `m_valorTotal`, `m_observaciones`, `m_stock_anterior`, `m_stock_actual`, `m_valor_anterior`, `m_valor_actual`, `i_id`, `e_id`, `c_id`, `u_id`, `id`, `created_at`, `updated_at`) VALUES ('2025-07-06 22:20:00','entrada',5,1.00,5.00,'',NULL,NULL,NULL,NULL,4,NULL,NULL,1,1,'2025-07-07 03:20:00','2025-07-07 03:20:00'),('2025-07-06 00:00:00','entrada',7,2.50,17.50,'Stock inicial del artículo ART005',NULL,NULL,NULL,NULL,5,NULL,NULL,1,2,'2025-07-07 03:22:06','2025-07-07 03:22:06'),('2025-07-06 22:22:36','entrada',6,2.50,15.00,'',NULL,NULL,NULL,NULL,5,NULL,NULL,1,3,'2025-07-07 03:22:36','2025-07-07 03:22:36');
/*!40000 ALTER TABLE `tb_movimiento_detalle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_persona`
--

DROP TABLE IF EXISTS `tb_persona`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_persona` (
  `pe_codigo` varchar(20) NOT NULL,
  `pe_nombre` varchar(100) NOT NULL,
  `pe_apellido` varchar(100) DEFAULT NULL,
  `pe_ci` varchar(20) DEFAULT NULL,
  `pe_telefono` varchar(15) DEFAULT NULL,
  `pe_correo` varchar(100) DEFAULT NULL,
  `pe_direccion` varchar(200) DEFAULT NULL,
  `pe_cargo` varchar(50) DEFAULT NULL,
  `pe_estado` varchar(20) DEFAULT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `pe_codigo` (`pe_codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_persona`
--

LOCK TABLES `tb_persona` WRITE;
/*!40000 ALTER TABLE `tb_persona` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_persona` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_proveedores`
--

DROP TABLE IF EXISTS `tb_proveedores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_proveedores` (
  `p_codigo` varchar(20) NOT NULL,
  `p_razonsocial` varchar(100) NOT NULL,
  `p_ci_ruc` varchar(13) NOT NULL,
  `p_direccion` varchar(200) DEFAULT NULL,
  `p_telefono` varchar(15) DEFAULT NULL,
  `p_correo` varchar(100) DEFAULT NULL,
  `p_estado` varchar(20) DEFAULT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `p_codigo` (`p_codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_proveedores`
--

LOCK TABLES `tb_proveedores` WRITE;
/*!40000 ALTER TABLE `tb_proveedores` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_proveedores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_stock`
--

DROP TABLE IF EXISTS `tb_stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_stock` (
  `s_cantidad` int DEFAULT NULL,
  `s_ultUpdt` datetime DEFAULT NULL,
  `i_id` int NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `i_id` (`i_id`),
  CONSTRAINT `tb_stock_ibfk_1` FOREIGN KEY (`i_id`) REFERENCES `tb_item` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_stock`
--

LOCK TABLES `tb_stock` WRITE;
/*!40000 ALTER TABLE `tb_stock` DISABLE KEYS */;
/*!40000 ALTER TABLE `tb_stock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tb_usuario`
--

DROP TABLE IF EXISTS `tb_usuario`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tb_usuario` (
  `u_username` varchar(50) NOT NULL,
  `u_password` varchar(255) NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `u_username` (`u_username`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_usuario`
--

LOCK TABLES `tb_usuario` WRITE;
/*!40000 ALTER TABLE `tb_usuario` DISABLE KEYS */;
INSERT INTO `tb_usuario` (`u_username`, `u_password`, `id`, `created_at`, `updated_at`) VALUES ('admin','pbkdf2:sha256:600000$L2ThhfpbJPIH9FPc$4530badd8578e43f339c9757657b63d0cc86a89b8feadfca39f0e1128c4c6d3a',1,'2025-07-07 03:05:53','2025-07-07 03:05:53');
/*!40000 ALTER TABLE `tb_usuario` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping routines for database 'sistema_inventario'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-07-09 11:39:05
