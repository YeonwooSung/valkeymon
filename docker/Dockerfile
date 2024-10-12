FROM mysql:5.7.12

ENV MYSQL_ROOT_PASSWORD valkeymon!@#
ENV MYSQL_USER valkeymon
ENV MYSQL_PASSWORD valkeymon!@#
ENV MYSQL_DATABASE valkeymon

COPY etc/ /etc/mysql/conf.d/
RUN cat /usr/share/zoneinfo/Asia/Seoul > /etc/localtime
