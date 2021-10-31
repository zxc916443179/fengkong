
#############################################################################

setwd("C:\\Users\\pc\\Desktop\\文件\\个人结算分析")
library(openxlsx)
library(gdata)

stock <- read.xlsx("沪深A股.xlsx",sheet=1)
person1 <- read.xlsx("分票汇总.xlsx",sheet=1)
person2 <- read.xlsx("分票汇总.xlsx",sheet=2)
person3 <- read.xlsx("分票汇总.xlsx",sheet=3)

detail1 <- read.xlsx("委托信息01-detail.xlsx",sheet=1)
detail2 <- read.xlsx("委托信息02-detail.xlsx",sheet=1)
detail3 <- read.xlsx("委托信息03-detail.xlsx",sheet=1)
today <- Sys.Date()
today <- as.character(today)
dir.create(today)
setwd(today)

##########################
ttl <- data.frame(x1=c("<3%",">3%",">5%",">8%","<3%",">3%",">5%",">8%","<3%",">3%",">5%",">8%"),x2=rep(0,12),x3=rep(0,12))
names(ttl) <- c("振幅","票数","占比")

##############################################################################
#Product No.1 
#amplitude percentage
total <- unique(person1[,2])
total <- as.data.frame(total)
names(total) <- c("名称")
total <- merge(total,stock,by="名称")
length <- dim(total)[1]
ttl[1,2] <- length(which(total[,4]<3))
ttl[1,3] <- ttl[1,2]/length
ttl[2,2] <- length(which((total[,4]>=3)&(total[,4]<5)))
ttl[2,3] <- ttl[2,2]/length
ttl[3,2] <- length(which((total[,4]>=5)&(total[,4]<8)))
ttl[3,3] <- ttl[3,2]/length
ttl[4,2] <- length(which(total[,4]>=8))
ttl[4,3] <- ttl[4,2]/length


#match
all <- merge(person1, stock, by="代码")
all <- all[order(-as.numeric(all$振幅)),]
nrows <- dim(all)[1]
count <- 0
for (i in 1:nrows)
{
  if (all[i,11]>=3)
  {
    count <- count+1
  }
  else
  {
    break
  }
}
all <- all[1:count,]

#Match Details

length_x <- dim(all)[1]

all <- within(all,{盈亏<-rep(0,length_x)})
options(digits=3)
for (i in 1:length_x)
{
  name <- all[i,2]
  trader <- all[i,6]
  length_y <- dim(detail1)[1]
  for (j in 1:length_y)
  {
    if ((detail1[j,6]==name)&&(detail1[j,11]==trader))
    {
      #options(digits=3)
      all[i,12] <- detail1[j,12]
      detail1 <- detail1[-j,]
      break
    }
  }
}
all <- all[,-(3:5)]
all <- all[,-4]
all <- all[,-(5:6)]
names(all) <- c("代码","名称","交易员","持仓市值","振幅","盈亏")
temp <- paste(today,"1号分析.xlsx",sep="-")
write.xlsx(all,temp)
#write.table(all,temp,sep="\t",row.names=FALSE,col.names=TRUE)



##############################################################################
#Product No.2
#amplitude percentage

total <- unique(person2[,2])
total <- as.data.frame(total)
names(total) <- c("名称")
total <- merge(total,stock,by="名称")
length <- dim(total)[1]
ttl[5,2] <- length(which(total[,4]<3))
ttl[5,3] <- ttl[5,2]/length
ttl[6,2] <- length(which((total[,4]>=3)&(total[,4]<5)))
ttl[6,3] <- ttl[6,2]/length
ttl[7,2] <- length(which((total[,4]>=5)&(total[,4]<8)))
ttl[7,3] <- ttl[7,2]/length
ttl[8,2] <- length(which(total[,4]>=8))
ttl[8,3] <- ttl[8,2]/length

#match
all <- merge(person2, stock, by="代码")
all <- all[order(-as.numeric(all$振幅)),]
nrows <- dim(all)[1]
count <- 0
for (i in 1:nrows)
{
  if (all[i,11]>=3)
  {
    count <- count+1
  }
  else
  {
    break
  }
}
all <- all[1:count,]

#Match Details

length_x <- dim(all)[1]

all <- within(all,{盈亏<-rep(0,length_x)})
options(digits=3)
for (i in 1:length_x)
{
  name <- all[i,2]
  trader <- all[i,6]
  length_y <- dim(detail2)[1]
  for (j in 1:length_y)
  {
    if ((detail2[j,6]==name)&&(detail2[j,11]==trader))
    {
      #options(digits=3)
      all[i,12] <- detail2[j,12]
      detail2 <- detail2[-j,]
      break
    }
  }
}
all <- all[,-(3:5)]
all <- all[,-4]
all <- all[,-(5:6)]
names(all) <- c("代码","名称","交易员","持仓市值","振幅","盈亏")
temp <- paste(today,"2号分析.xlsx",sep="-")
write.xlsx(all,temp)
#write.table(all,temp,sep="\t",row.names=FALSE,col.names=TRUE)


##############################################################################
#Product No.3
#amplitude percentage

total <- unique(person3[,2])
total <- as.data.frame(total)
names(total) <- c("名称")
total <- merge(total,stock,by="名称")
length <- dim(total)[1]
ttl[9,2] <- length(which(total[,4]<3))
ttl[9,3] <- ttl[9,2]/length
ttl[10,2] <- length(which((total[,4]>=3)&(total[,4]<5)))
ttl[10,3] <- ttl[10,2]/length
ttl[11,2] <- length(which((total[,4]>=5)&(total[,4]<8)))
ttl[11,3] <- ttl[11,2]/length
ttl[12,2] <- length(which(total[,4]>=8))
ttl[12,3] <- ttl[12,2]/length

#match
all <- merge(person3, stock, by="代码")
all <- all[order(-as.numeric(all$振幅)),]
nrows <- dim(all)[1]
count <- 0
for (i in 1:nrows)
{
  if (all[i,11]>=3)
  {
    count <- count+1
  }
  else
  {
    break
  }
}
all <- all[1:count,]

#Match Details

length_x <- dim(all)[1]

all <- within(all,{盈亏<-rep(0,length_x)})
options(digits=3)
for (i in 1:length_x)
{
  name <- all[i,2]
  trader <- all[i,6]
  length_y <- dim(detail3)[1]
  for (j in 1:length_y)
  {
    if ((detail3[j,6]==name)&&(detail3[j,11]==trader))
    {
      #options(digits=3)
      all[i,12] <- detail3[j,12]
      detail3 <- detail3[-j,]
      break
    }
  }
}
all <- all[,-(3:5)]
all <- all[,-4]
all <- all[,-(5:6)]
names(all) <- c("代码","名称","交易员","持仓市值","振幅","盈亏")
temp <- paste(today,"3号分析.xlsx",sep="-")
write.xlsx(all,temp)
#write.table(all,temp,sep="\t",row.names=FALSE,col.names=TRUE)


write.table(ttl,"振幅占比.xlsx",sep="\t",row.names=FALSE,col.names=TRUE)
